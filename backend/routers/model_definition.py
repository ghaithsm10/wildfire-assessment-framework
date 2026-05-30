import torch
import torch.nn as nn
import torch.nn.functional as F

class ChannelAttention(nn.Module):
    """Attention sur les canaux pour pondérer les features importantes"""
    def __init__(self, in_channels, reduction=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        
        self.fc = nn.Sequential(
            nn.Conv2d(in_channels, in_channels // reduction, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(in_channels // reduction, in_channels, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        out = self.sigmoid(avg_out + max_out)
        return x * out

class SpatialAttention(nn.Module):
    """Attention spatiale pour se concentrer sur les zones importantes"""
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x_cat = torch.cat([avg_out, max_out], dim=1)
        attention = self.sigmoid(self.conv(x_cat))
        return x * attention

class CBAM(nn.Module):
    """Convolutional Block Attention Module - Attention complète"""
    def __init__(self, in_channels, reduction=16):
        super(CBAM, self).__init__()
        self.channel_attention = ChannelAttention(in_channels, reduction)
        self.spatial_attention = SpatialAttention()
    
    def forward(self, x):
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x

class ResidualBlock(nn.Module):
    """Bloc résiduel amélioré avec attention"""
    def __init__(self, channels, use_attention=True):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.use_attention = use_attention
        if use_attention:
            self.attention = CBAM(channels)
        
    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.use_attention:
            out = self.attention(out)
        out += residual
        return F.relu(out)

class Encoder(nn.Module):
    """Encodeur AMÉLIORÉ avec plus de capacité"""
    def __init__(self, input_channels=7, latent_dim=512):
        super(Encoder, self).__init__()
        
        # Bloc initial - extraction de features de base
        self.conv1 = nn.Sequential(
            nn.Conv2d(input_channels, 64, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True),
            ResidualBlock(64, use_attention=True)
        )
        self.pool1 = nn.MaxPool2d(2, 2)
        
        # Bloc 2 - features de niveau moyen
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),
            ResidualBlock(128, use_attention=True),
            ResidualBlock(128, use_attention=False)
        )
        self.pool2 = nn.MaxPool2d(2, 2)
        
        # Bloc 3 - features complexes
        self.conv3 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),
            ResidualBlock(256, use_attention=True),
            ResidualBlock(256, use_attention=False)
        )
        self.pool3 = nn.MaxPool2d(2, 2)
        
        # Bloc 4 - features de haut niveau
        self.conv4 = nn.Sequential(
            nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
            ResidualBlock(512, use_attention=True)
        )
        self.pool4 = nn.MaxPool2d(2, 2)
        
        # Bloc 5 - compression maximale
        self.conv5 = nn.Sequential(
            nn.Conv2d(512, 512, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
        )
        
        self.adaptive_pool = nn.AdaptiveAvgPool2d((8, 8))
        
        # Couches latentes avec dropout pour régularisation
        self.dropout = nn.Dropout(0.2)
        self.fc_mu = nn.Linear(512 * 8 * 8, latent_dim)
        self.fc_log_var = nn.Linear(512 * 8 * 8, latent_dim)
        
    def forward(self, x):
        x = self.conv1(x)
        x = self.pool1(x)
        x = self.conv2(x)
        x = self.pool2(x)
        x = self.conv3(x)
        x = self.pool3(x)
        x = self.conv4(x)
        x = self.pool4(x)
        x = self.conv5(x)
        x = self.adaptive_pool(x)
        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        mu = self.fc_mu(x)
        log_var = self.fc_log_var(x)
        return mu, log_var


class Decoder(nn.Module):
    """Décodeur AMÉLIORÉ avec skip connections conceptuelles"""
    def __init__(self, latent_dim=512, output_channels=7):
        super(Decoder, self).__init__()
        
        self.fc = nn.Sequential(
            nn.Linear(latent_dim, 512 * 8 * 8),
            nn.LeakyReLU(0.2, inplace=True)
        )
        
        # Upsampling progressif avec attention
        self.up1 = nn.Sequential(
            nn.ConvTranspose2d(512, 512, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            ResidualBlock(512, use_attention=True)
        )
        
        self.up2 = nn.Sequential(
            nn.ConvTranspose2d(512, 256, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            ResidualBlock(256, use_attention=True),
            ResidualBlock(256, use_attention=False)
        )
        
        self.up3 = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            ResidualBlock(128, use_attention=True),
            ResidualBlock(128, use_attention=False)
        )
        
        self.up4 = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            ResidualBlock(64, use_attention=False)
        )
        
        # Branche de reconstruction des 6 bandes
        self.recon_conv = nn.Sequential(
            nn.Conv2d(64, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, output_channels, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        
        # Branche de risk map - ARCHITECTURE SPÉCIALISÉE
        self.risk_conv1 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            ResidualBlock(64, use_attention=True)
        )
        
        self.risk_conv2 = nn.Sequential(
            nn.Conv2d(64, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 16, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, kernel_size=1),
            nn.Sigmoid()
        )
        
    def forward(self, z, target_size):
        x = self.fc(z)
        x = x.view(x.size(0), 512, 8, 8)
        
        x = self.up1(x)  # 512, 16, 16
        x = self.up2(x)  # 256, 32, 32
        x = self.up3(x)  # 128, 64, 64
        x = self.up4(x)  # 64, 128, 128
        
        # Reconstruction des 6 bandes
        recon_features = self.recon_conv(x)
        recon = F.interpolate(recon_features, size=target_size, mode='bilinear', align_corners=False)
        recon = torch.clamp(recon, min=0.0, max=1.0)
        
        # Risk map avec traitement spécialisé
        risk_features = self.risk_conv1(x)
        risk_features = self.risk_conv2(risk_features)
        risk_map = F.interpolate(risk_features, size=target_size, mode='bilinear', align_corners=False)
        risk_map = torch.clamp(risk_map, min=0.0, max=1.0)
        
        return recon, risk_map


class VAE_FireRisk(nn.Module):
    """VAE OPTIMISÉ pour prédiction de risque d'incendie"""
    def __init__(self, input_channels=7, latent_dim=512):
        super(VAE_FireRisk, self).__init__()
        self.encoder = Encoder(input_channels, latent_dim)
        self.decoder = Decoder(latent_dim, output_channels=input_channels)
        self.latent_dim = latent_dim
        self.input_channels = input_channels
        
    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def forward(self, x):
        target_size = (x.shape[2], x.shape[3])
        mu, log_var = self.encoder(x)
        z = self.reparameterize(mu, log_var)
        recon, risk_map = self.decoder(z, target_size)
        return recon, risk_map, mu, log_var
    
    def predict_risk(self, x):
        """Prédiction stable sans sampling"""
        with torch.no_grad():
            target_size = (x.shape[2], x.shape[3])
            mu, _ = self.encoder(x)
            _, risk_map = self.decoder(mu, target_size)
        return risk_map


def dice_loss(pred, target, smooth=1e-6):
    """Dice loss pour segmentation - meilleur pour zones à risque"""
    pred = pred.contiguous()
    target = target.contiguous()
    intersection = (pred * target).sum(dim=(2, 3))
    dice = (2. * intersection + smooth) / (pred.sum(dim=(2, 3)) + target.sum(dim=(2, 3)) + smooth)
    return 1 - dice.mean()


def focal_loss(pred, target, alpha=0.25, gamma=2.0):
    """Focal Loss amélioré"""
    pred = torch.clamp(pred, min=1e-7, max=1.0 - 1e-7)
    target = torch.clamp(target, min=0.0, max=1.0)
    
    bce = F.binary_cross_entropy(pred, target, reduction='none')
    pt = torch.exp(-bce)
    focal = alpha * (1 - pt) ** gamma * bce
    return focal.mean()


def tversky_loss(pred, target, alpha=0.7, beta=0.3, smooth=1e-6):
    """Tversky loss - bon pour déséquilibre de classes"""
    pred = pred.contiguous()
    target = target.contiguous()
    
    TP = (pred * target).sum(dim=(2, 3))
    FP = (pred * (1 - target)).sum(dim=(2, 3))
    FN = ((1 - pred) * target).sum(dim=(2, 3))
    
    tversky = (TP + smooth) / (TP + alpha * FP + beta * FN + smooth)
    return 1 - tversky.mean()


def edge_aware_smoothness_loss(risk_map, image):
    """Smoothness loss qui respecte les bords"""
    img_gray = image.mean(dim=1, keepdim=True)
    
    # Gradients image
    img_dx = torch.abs(img_gray[:, :, :, :-1] - img_gray[:, :, :, 1:])
    img_dy = torch.abs(img_gray[:, :, :-1, :] - img_gray[:, :, 1:, :])
    
    # Gradients risk map
    risk_dx = risk_map[:, :, :, :-1] - risk_map[:, :, :, 1:]
    risk_dy = risk_map[:, :, :-1, :] - risk_map[:, :, 1:, :]
    
    # Pénaliser les gradients sauf aux bords
    edge_weight = 2.0
    smoothness_x = torch.mean(risk_dx ** 2 * torch.exp(-edge_weight * img_dx))
    smoothness_y = torch.mean(risk_dy ** 2 * torch.exp(-edge_weight * img_dy))
    
    return smoothness_x + smoothness_y


def pseudo_supervised_loss(recon_x, x, risk_map, pseudo_label, mu, log_var, 
                          beta=0.5, gamma=4.0, lambda_smooth=0.2):
    batch_size = x.size(0)
    
    # Conversion avec clipping AGRESSIF
    recon_x = torch.clamp(recon_x.float(), 1e-7, 1.0 - 1e-7)  # ← Plus strict
    x = torch.clamp(x.float(), 0.0, 1.0)
    risk_map = torch.clamp(risk_map.float(), 1e-7, 1.0 - 1e-7)  # ← Plus strict
    pseudo_label = torch.clamp(pseudo_label.float(), 0.0, 1.0)
    
    # Vérifier NaN
    if torch.isnan(recon_x).any() or torch.isnan(risk_map).any():
        print("⚠️ NaN détecté dans les prédictions!")
        return torch.tensor(0.0, requires_grad=True), 0, 0, 0, 0, 0
    
    mu = mu.float()
    log_var = torch.clamp(log_var.float(), -10, 10)  # ← Limiter log_var
    
    # 1. RECONSTRUCTION LOSS
    recon_loss_mse = F.mse_loss(recon_x, x, reduction='mean')
    recon_loss_l1 = F.l1_loss(recon_x, x, reduction='mean')
    
    # Perceptual loss avec vérification
    x_dx = x[:, :, :, :-1] - x[:, :, :, 1:]
    x_dy = x[:, :, :-1, :] - x[:, :, 1:, :]
    recon_dx = recon_x[:, :, :, :-1] - recon_x[:, :, :, 1:]
    recon_dy = recon_x[:, :, :-1, :] - recon_x[:, :, 1:, :]
    perceptual = F.l1_loss(recon_dx, x_dx) + F.l1_loss(recon_dy, x_dy)
    
    recon_loss = 0.5 * recon_loss_mse + 0.3 * recon_loss_l1 + 0.2 * perceptual
    
    # 2. KL DIVERGENCE avec clipping FORT
    kl_loss = -0.5 * torch.mean(1 + log_var - mu.pow(2) - log_var.exp())
    kl_loss = torch.clamp(kl_loss, min=0.0, max=5.0)  # ← Plus strict (5 au lieu de 10)
    
    # 3. RISK LOSS
    focal = focal_loss(risk_map, pseudo_label, alpha=0.25, gamma=2.0)
    dice = dice_loss(risk_map, pseudo_label)
    mse_risk = F.mse_loss(risk_map, pseudo_label)
    
    risk_loss = 0.5 * focal + 0.3 * dice + 0.2 * mse_risk
    
    # 4. SMOOTHNESS avec clipping
    smoothness_loss = edge_aware_smoothness_loss(risk_map, x)
    smoothness_loss = torch.clamp(smoothness_loss, max=1.0)  # ← Limiter
    
    # 5. CONTRAST
    risk_std = torch.std(risk_map)
    contrast_loss = -risk_std
    
    # 6. DISTRIBUTION
    risk_mean = risk_map.mean()
    distribution_penalty = (risk_mean - 0.5).abs()
    
    # TOTAL LOSS avec pondérations RÉDUITES
    total_loss = (
        1.5 * recon_loss +              # Réduit: 1.5 au lieu de 2.0
        beta * kl_loss +                # KL avec annealing
        gamma * risk_loss +             # Réduit par défaut (gamma=4.0)
        lambda_smooth * smoothness_loss + # Réduit par défaut (0.2)
        0.05 * contrast_loss +          # Réduit: 0.05 au lieu de 0.1
        0.02 * distribution_penalty      # Réduit: 0.02 au lieu de 0.05
    )
    
    # Vérification finale
    if not torch.isfinite(total_loss):
        print("⚠️ Loss non-finie calculée!")
        return torch.tensor(0.0, requires_grad=True), 0, 0, 0, 0, 0
    
    return (total_loss, 
            recon_loss.item(), 
            kl_loss.item(), 
            risk_loss.item(), 
            smoothness_loss.item(),
            contrast_loss.item())


if __name__ == "__main__":
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("="*70)
    print("TEST DU MODÈLE VAE AMÉLIORÉ - 7 BANDES")
    print("="*70)
    
    model = VAE_FireRisk(input_channels=7, latent_dim=512).to(device)
    
    # Test
    test_input = torch.randn(2, 7, 410, 751).to(device)
    print(f"\nInput: {test_input.shape}")
    
    with torch.no_grad():
        recon, risk_map, mu, log_var = model(test_input)
    
    print(f"Reconstruction: {recon.shape}")
    print(f"Risk map: {risk_map.shape}")
    
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"\nParamètres totaux: {total_params:,}")
    print(f"Paramètres entraînables: {trainable_params:,}")
    print(f"Mémoire: ~{total_params * 4 / 1024 / 1024:.1f} MB")
    
    print("\n" + "="*70)
    print("✅ MODÈLE AMÉLIORÉ VALIDÉ!")
    print("="*70)
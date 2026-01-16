# RoXX - FreeRADIUS Integration Guide

## 🔌 Intégration avec FreeRADIUS

Les modules d'authentification Python peuvent être utilisés directement avec FreeRADIUS via le module `exec`.

---

## 📦 Modules Disponibles

### 1. inWebo Push Authentication

**Script**: `python -m roxx.core.auth.inwebo`

**Configuration FreeRADIUS** (`/etc/freeradius/3.0/mods-enabled/exec`):

```
exec inwebo_push {
    wait = yes
    program = "python3 -m roxx.core.auth.inwebo"
    input_pairs = request
    output_pairs = reply
    shell_escape = yes
}
```

**Variables d'environnement requises**:
- `USER_NAME` - Nom d'utilisateur (fourni par FreeRADIUS)
- `INWEBO_SERVICE_ID` - ID du service inWebo (défaut: 10408)
- `INWEBO_PROXY` - URL du proxy (optionnel)

**Certificats requis**:
- `C:\ProgramData\RoXX\certs\iw_cert.pem` (Windows)
- `/usr/local/etc/certs/iw_cert.pem` (Linux)
- `C:\ProgramData\RoXX\certs\iw_key.pem` (Windows)
- `/usr/local/etc/certs/iw_key.pem` (Linux)

**Codes de retour**:
- `OK` - Authentification réussie (exit 0)
- `REFUSED` - Utilisateur a refusé (exit 1)
- `TIMEOUT` - Timeout (exit 1)
- `ERROR` - Erreur technique (exit 1)

---

### 2. TOTP Authentication

**Script**: `python -m roxx.core.auth.totp`

**Configuration FreeRADIUS**:

```
exec totp_auth {
    wait = yes
    program = "python3 -m roxx.core.auth.totp"
    input_pairs = request
    output_pairs = reply
    shell_escape = yes
}
```

**Variables d'environnement requises**:
- `USER_NAME` - Nom d'utilisateur
- `USER_PASSWORD` - Code TOTP à vérifier

**Fichier de secrets** (`totp_secrets.txt`):
```
# Format: username:secret_base32
john:JBSWY3DPEHPK3PXP
alice:MFRGGZDFMZTWQ2LK
```

**Codes de retour**:
- `OK` - Code valide (exit 0)
- `INVALID` - Code invalide (exit 1)
- `NOSECRET` - Pas de secret pour cet utilisateur (exit 1)

---

### 3. EntraID/Azure AD Authentication

**Script**: `python -m roxx.core.auth.entraid`

**Configuration FreeRADIUS**:

```
exec entraid_auth {
    wait = yes
    program = "python3 -m roxx.core.auth.entraid"
    input_pairs = request
    output_pairs = reply
    shell_escape = yes
}
```

**Variables d'environnement requises**:
- `USER_NAME` - Nom d'utilisateur (sera suffixé avec @domain)
- `USER_PASSWORD` - Mot de passe

**Configuration dans le script**:
- Modifier `authority` avec votre tenant ID
- Modifier `client_id` avec votre application ID
- Modifier le domaine dans le script

---

## 🔧 Configuration Complète

### Exemple: Site FreeRADIUS avec Multi-Auth

```
server default {
    authorize {
        # Vérifier le type d'auth demandé
        if (User-Name =~ /^totp:/) {
            update control {
                Auth-Type := TOTP
            }
        }
        elsif (User-Name =~ /^push:/) {
            update control {
                Auth-Type := PUSH
            }
        }
        elsif (User-Name =~ /^azure:/) {
            update control {
                Auth-Type := AZURE
            }
        }
    }

    authenticate {
        Auth-Type TOTP {
            totp_auth
        }
        
        Auth-Type PUSH {
            inwebo_push
        }
        
        Auth-Type AZURE {
            entraid_auth
        }
    }
}
```

---

## 🧪 Tests

### Test inWebo (Linux)
```bash
export USER_NAME="john.doe"
export INWEBO_SERVICE_ID="10408"
python3 -m roxx.core.auth.inwebo
echo "Exit code: $?"
```

### Test TOTP (Linux)
```bash
export USER_NAME="john"
export USER_PASSWORD="123456"
python3 -m roxx.core.auth.totp
echo "Exit code: $?"
```

### Test EntraID (Linux)
```bash
export USER_NAME="john.doe"
export USER_PASSWORD="MyPassword123!"
python3 -m roxx.core.auth.entraid
echo "Exit code: $?"
```

### Test sur Windows (PowerShell)
```powershell
$env:USER_NAME = "john.doe"
$env:INWEBO_SERVICE_ID = "10408"
python -m roxx.core.auth.inwebo
Write-Host "Exit code: $LASTEXITCODE"
```

---

## 📝 Logs

Les modules utilisent le système de logging Python. Pour voir les logs:

**Linux** (syslog):
```bash
tail -f /var/log/syslog | grep -E "inwebo|totp|entraid"
```

**Windows** (Event Viewer):
- Les logs sont écrits dans la sortie standard
- Configurer FreeRADIUS pour rediriger vers un fichier

---

## 🔒 Sécurité

### Permissions des fichiers

**Linux**:
```bash
# Certificats inWebo
chmod 600 /usr/local/etc/certs/iw_*.pem
chown freeradius:freeradius /usr/local/etc/certs/iw_*.pem

# Secrets TOTP
chmod 600 /usr/local/etc/totp_secrets.txt
chown freeradius:freeradius /usr/local/etc/totp_secrets.txt
```

**Windows**:
- Utiliser les ACL pour restreindre l'accès aux certificats
- Seul le compte de service FreeRADIUS doit avoir accès

---

## 🚀 Migration depuis Bash

### Remplacement de push.sh

**Avant** (Bash):
```bash
exec push_auth {
    program = "/usr/local/bin/push.sh"
}
```

**Après** (Python):
```bash
exec push_auth {
    program = "python3 -m roxx.core.auth.inwebo"
}
```

### Avantages
- ✅ Multi-OS (Windows/Linux/macOS)
- ✅ Meilleure gestion d'erreurs
- ✅ Logging structuré
- ✅ Pas de dépendance à curl/jq
- ✅ Tests unitaires possibles

---

## 📚 Références

- [FreeRADIUS exec module](https://wiki.freeradius.org/modules/Rlm_exec)
- [inWebo API Documentation](https://www.inwebo.com/documentation/)
- [RFC 6238 - TOTP](https://tools.ietf.org/html/rfc6238)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)

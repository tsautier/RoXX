# SAML 2.0 SSO Setup Guide

This guide explains how to configure SAML 2.0 Single Sign-On with RoXX.

---

## Overview

RoXX acts as a **Service Provider (SP)** and integrates with your existing **Identity Provider (IdP)** such as:
- Okta
- Azure AD / Entra ID
- Google Workspace
- OneLogin
- SimpleSAMLphp
- Any SAML 2.0 compliant IdP

---

## Prerequisites

1. Access to your IdP admin console
2. RoXX admin access
3. Valid SSL certificate (required for production SAML)
4. SP Entity ID (your RoXX domain, e.g., `https://auth.company.com`)

---

## Configuration Steps

### Step 1: Add SAML Provider in RoXX

1. Login to RoXX admin portal
2. Navigate to **Config → Authentication Providers**
3. Click **+ Add Provider**
4. Select **SAML 2.0**
5. Enter provider information (see below)

### Step 2: Configure SP Information

RoXX provides two important endpoints for your IdP configuration:

#### Service Provider Metadata
```
https://your-domain.com/auth/saml/metadata/{provider_id}
```

#### Assertion Consumer Service (ACS) URL  
```
https://your-domain.com/auth/saml/acs/{provider_id}
```

**Note**: `{provider_id}` will be assigned when you save the provider.

### Step 3: Configure IdP Settings in RoXX

Fill in the following fields:

#### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Display name for this provider | "Corporate SSO" |
| **IdP Entity ID** | Unique identifier of your IdP | `https://idp.example.com` |
| **IdP SSO URL** | Single Sign-On endpoint | `https://idp.example.com/sso` |
| **IdP x509 Certificate** | Public certificate from IdP | See certificate format below |
| **SP Entity ID** | Your RoXX domain | `https://auth.company.com` |
| **Attribute Mapping** | Username attribute | `uid`, `email`, or `NameID` |

#### Certificate Format

The IdP x509 certificate should be in PEM format:

```
-----BEGIN CERTIFICATE-----
MIIDdDCCAlygAwIBAgIJALoZxJTY8...
[certificate content]
...
-----END CERTIFICATE-----
```

**Where to find it:**
- **Okta**: Admin → Security → Identity Providers → Download Certificate
- **Azure AD**: Azure Portal → App Registrations → Certificates
- **Google**: Admin Console → Apps → SAML apps → Download Certificate

###

 Step 4: Configure Your IdP

Upload RoXX's SP metadata to your IdP:

1. Download metadata from: `https://your-domain.com/auth/saml/metadata/1`
2. Or manually configure:
   - **ACS URL**: `https://your-domain.com/auth/saml/acs/1`
   - **SP Entity ID**: `https://auth.company.com`
   - **Name ID Format**: `urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified`

---

## Provider-Specific Guides

### Okta

1. **Create SAML Application**
   - Admin Console → Applications → Create App Integration
   - Select "SAML 2.0"
   
2. **Configure SAML Settings**
   - Single Sign-On URL: `https://your-domain.com/auth/saml/acs/1`
   - Audience URI: `https://auth.company.com`
   
3. **Attribute Statements**
   - Create mapping for username: `user.login` → `uid`

4. **Download Certificate**
   - Sign On → SAML Signing Certificates → Download

### Azure AD / Entra ID

1. **Register Enterprise Application**
   - Azure Portal → Enterprise Applications → New Application
   - Create your own application
   
2. **Configure SSO**
   - Single Sign-On → SAML
   - Identifier: `https://auth.company.com`
   - Reply URL: `https://your-domain.com/auth/saml/acs/1`
   
3. **User Attribute**
   - Claim name: `uid`
   - Source: `user.userprincipalname`

4. **Download Certificate**
   - SAML Signing Certificate → Certificate (Base64)

### Google Workspace

1. **Add SAML App**
   - Admin Console → Apps → Web and mobile apps → Add app → Custom SAML app
   
2. **IdP Configuration**
   - Download metadata or copy SSO URL and certificate
   
3. **Service Provider Details**
   - ACS URL: `https://your-domain.com/auth/saml/acs/1`
   - Entity ID: `https://auth.company.com`
   - Name ID: Basic Information > Primary Email
   
4. **Attribute Mapping**
   - Map "Email" to `uid`

---

## Attribute Mapping

RoXX requires a username attribute from the SAML assertion. Configure this in the **Attribute Mapping** field.

### Common Mappings

| IdP | Recommended Attribute |
|-----|----------------------|
| Okta | `uid` or `user.login` |
| Azure AD | `uid` or `userprincipalname` |
| Google | `uid` or `email` |
| Generic | `NameID` |

**Example SAML Assertion:**
```xml
<saml:Attribute Name="uid">
    <saml:AttributeValue>john.doe</saml:AttributeValue>
</saml:Attribute>
```

---

## Testing

### Test Connection

1. In RoXX provider configuration, click **Test Connection**
2. Should show success message
3. Verify certificate is valid

### Test Login Flow

1. Navigate to: `https://your-domain.com/auth/saml/login/1`
2. Should redirect to IdP login page
3. Login with valid credentials
4. Should redirect back to RoXX
5. Verify user is created in RoXX

### Verify User Creation

After successful SAML login:
1. Go to **User Management**
2. Find the newly created user
3. Verify username matches SAML attribute
4. Check **Auth Source** is "SAML"

---

## Troubleshooting

### Common Issues

#### Metadata Not Loading
**Symptom**: IdP cannot fetch metadata  
**Solution**:
- Verify RoXX is accessible from internet
- Check SSL certificate is valid
- Ensure no firewall blocking

#### Certificate Mismatch
**Symptom**: "Invalid signature" error  
**Solution**:
- Verify certificate copied correctly (no extra spaces/newlines)
- Ensure certificate matches IdP configuration
- Check certificate hasn't expired

#### Attribute Not Found
**Symptom**: User creation fails  
**Solution**:
- Check attribute name matches IdP configuration
- Verify attribute is included in SAML assertion
- Review logs at `/config/auth-providers/logs`

#### Loop Redirect
**Symptom**: Continuous redirect between SP and IdP  
**Solution**:
- Verify ACS URL matches exactly
- Check SP Entity ID is consistent
- Clear browser cookies and try again

### Debug Logs

Enable debug logging to see full SAML requests/responses:

```bash
export ROXX_DEBUG=true
python3 -m roxx.web.app
```

View logs at: **Config → Auth Providers → View Debug Logs**

---

## Security Considerations

### Certificate Validation
- ✅ Always validate IdP certificate
- ✅ Use HTTPS for all SAML endpoints
- ✅ Regularly rotate certificates

### Assertion Validation
- ✅ Verify signature on assertions
- ✅ Check assertion expiry
- ✅ Validate ACS URL matches

### User Provisioning
- ✅ Verify user attributes before creation
- ✅ Implement just-in-time (JIT) provisioning
- ✅ Review created users regularly

---

## Advanced Configuration

### Multiple IdPs

You can configure multiple SAML providers for different user groups:

1. Create separate providers for each IdP
2. Each gets unique metadata URL and ACS URL
3. Users choose provider at login

### Custom Attribute Mapping

Map additional SAML attributes for user profile:

```python
# Future enhancement
attribute_mapping = {
    "username": "uid",
    "email": "mail",
    "display_name": "displayName"
}
```

---

## Support

For SAML integration issues:
1. Check debug logs
2. Verify configuration with IdP admin
3. Open GitHub issue with logs (redact sensitive data)

---

**Last Updated**: 2026-01-21  
**Version**: 1.0.0-beta5

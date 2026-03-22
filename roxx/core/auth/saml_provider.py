"""
SAML 2.0 Authentication Provider
Implements SAML Service Provider (SP) functionality for SSO integration
"""

import logging
from typing import Dict, Tuple, Optional
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

logger = logging.getLogger(__name__)

class SAMLProvider:
    """SAML 2.0 Service Provider implementation"""
    
    def __init__(self, config: Dict):
        """
        Initialize SAML provider with configuration
        
        Args:
            config: Dict containing:
                - idp_entity_id: Identity Provider Entity ID
                - idp_sso_url: IdP Single Sign-On URL
                - idp_slo_url: IdP Single Logout URL (optional)
                - idp_x509_cert: IdP x509 certificate
                - sp_entity_id: Service Provider Entity ID
                - sp_acs_url: Assertion Consumer Service URL
                - sp_slo_url: SP Single Logout URL (optional)
        """
        self.config = config
        self._validate_config()
        
    def _validate_config(self):
        """Validate required SAML configuration fields"""
        required = ['idp_entity_id', 'idp_sso_url', 'idp_x509_cert', 
                   'sp_entity_id', 'sp_acs_url']
        for field in required:
            if field not in self.config:
                raise ValueError(f"Missing required SAML config field: {field}")
    
    def get_saml_settings(self, request_data: Dict) -> Dict:
        """
        Generate python3-saml settings dict
        
        Args:
            request_data: Request context (url, query_string, etc)
            
        Returns:
            Settings dictionary for OneLogin_Saml2_Auth
        """
        settings = {
            'strict': True,
            'debug': False,
            'sp': {
                'entityId': self.config['sp_entity_id'],
                'assertionConsumerService': {
                    'url': self.config['sp_acs_url'],
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
            },
            'idp': {
                'entityId': self.config['idp_entity_id'],
                'singleSignOnService': {
                    'url': self.config['idp_sso_url'],
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': self.config['idp_x509_cert']
            },
            'security': {
                'nameIdEncrypted': False,
                'authnRequestsSigned': False,
                'logoutRequestSigned': False,
                'logoutResponseSigned': False,
                'signMetadata': False,
                'wantMessagesSigned': False,
                'wantAssertionsSigned': True,
                'wantNameIdEncrypted': False,
                'requestedAuthnContext': True
            }
        }
        
        # Add SLO if configured
        if self.config.get('sp_slo_url'):
            settings['sp']['singleLogoutService'] = {
                'url': self.config['sp_slo_url'],
                'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
            }
        
        if self.config.get('idp_slo_url'):
            settings['idp']['singleLogoutService'] = {
                'url': self.config['idp_slo_url'],
                'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
            }
        
        return settings
    
    def initiate_sso(self, request_data: Dict, relay_state: str = None) -> str:
        """
        Generate SAML authentication request and return redirect URL
        
        Args:
            request_data: Request context
            relay_state: Optional relay state for post-auth redirect
            
        Returns:
            URL to redirect user to IdP
        """
        settings = self.get_saml_settings(request_data)
        auth = OneLogin_Saml2_Auth(request_data, settings)
        return auth.login(return_to=relay_state)
    
    def process_response(self, request_data: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Process SAML response from IdP
        
        Args:
            request_data: Request context with POST data
            
        Returns:
            Tuple of (success, user_attributes, error_message)
            user_attributes contains: email, username, groups, etc.
        """
        settings = self.get_saml_settings(request_data)
        auth = OneLogin_Saml2_Auth(request_data, settings)
        
        auth.process_response()
        errors = auth.get_errors()
        
        if errors:
            error_msg = f"SAML authentication failed: {', '.join(errors)}"
            logger.error(error_msg)
            return False, None, error_msg
        
        if not auth.is_authenticated():
            return False, None, "User not authenticated"
        
        # Extract user attributes
        attributes = auth.get_attributes()
        nameid = auth.get_nameid()
        
        user_data = {
            'email': nameid,  # NameID is typically email
            'username': attributes.get('uid', [nameid])[0] if attributes.get('uid') else nameid,
            'first_name': attributes.get('givenName', [''])[0] if attributes.get('givenName') else '',
            'last_name': attributes.get('sn', [''])[0] if attributes.get('sn') else '',
            'groups': attributes.get('groups', []) if attributes.get('groups') else [],
            'raw_attributes': attributes
        }
        
        logger.info(f"SAML authentication successful for {user_data['email']}")
        return True, user_data, None
    
    def get_metadata(self) -> str:
        """
        Generate SP metadata XML
        
        Returns:
            XML metadata string
        """
        # Create minimal request_data for metadata generation
        request_data = {
            'https': 'on' if 'https://' in self.config['sp_acs_url'] else 'off',
            'http_host': self.config['sp_acs_url'].split('/')[2],
            'script_name': '',
            'server_port': 443 if 'https://' in self.config['sp_acs_url'] else 80,
        }
        
        settings = self.get_saml_settings(request_data)
        saml_settings = OneLogin_Saml2_Settings(settings=settings)
        metadata = saml_settings.get_sp_metadata()
        
        errors = saml_settings.validate_metadata(metadata)
        if errors:
            raise ValueError(f"Invalid SP metadata: {', '.join(errors)}")
        
        return metadata
    
    @staticmethod
    def test_connection(config: Dict, test_username: str = None, test_password: str = None) -> Tuple[bool, str]:
        """
        Test SAML configuration (metadata generation only, no actual SSO)
        
        Args:
            config: SAML configuration dict
            test_username: Ignored for SAML (SSO initiated via browser)
            test_password: Ignored for SAML
            
        Returns:
            Tuple of (success, message)
        """
        try:
            provider = SAMLProvider(config)
            metadata = provider.get_metadata()
            
            if metadata and len(metadata) > 100:  # Basic sanity check
                return True, "SAML configuration valid. Metadata generated successfully."
            else:
                return False, "Generated metadata appears invalid"
                
        except Exception as e:
            logger.error(f"SAML test connection failed: {e}")
            return False, f"Configuration error: {str(e)}"

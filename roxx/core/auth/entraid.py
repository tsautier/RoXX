"""
EntraID (Azure AD) Authentication Module
Authenticates users against Microsoft EntraID/Azure AD
"""

import os
import sys
import msal
import logging


def main():
    if 'USER_NAME' not in os.environ:   
        logging.warning('ENTRAID-AUTH : '+'USERNAME MISSING')
        sys.exit(2)

    if 'USER_PASSWORD' not in os.environ:
        logging.warning('ENTRAID-AUTH : '+'PASSWORD MISSING, check PAP is enabled')
        sys.exit(2)

    app = msal.PublicClientApplication(
        authority='https://login.microsoftonline.com/599aef70-305b-4efb-aeba-161ae3e6c4fa',
        client_id='09594de9-4c6f-4407-8b01-a0286ddbe70b',
        client_credential=None
    )
    result = app.acquire_token_by_username_password(
        os.environ['USER_NAME'].strip('\"') + '@tuxy80.onmicrosoft.com'
        , os.environ['USER_PASSWORD'].strip('\"')
        , scopes = ['User.Read'])

    if 'access_token' in result:
        #access_token = result['access_token']
        logging.info('ENTRAID-AUTH : '+'Success AUTH for '+os.environ['USER_NAME'])
        print('Auth-Type = Accept\nReply-Message = OK')
        sys.exit(0)
    else:
        print('Auth-Type = PAP')
        logging.info('ENTRAID-AUTH : '+os.environ['USER_NAME']+result.get('error_description'))
        sys.exit(1)

if __name__ == "__main__":
    main()



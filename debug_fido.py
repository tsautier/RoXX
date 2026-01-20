
try:
    from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
    print("Import successful")
    
    try:
        rp = PublicKeyCredentialRpEntity(id="localhost", name="RoXX")
        print("Success: Positional args")
    except Exception as e:
        print(f"Failed Positional: {e}")
        
    try:
        rp = PublicKeyCredentialRpEntity("localhost", "RoXX")
        print("Success: Positional args (implicit)")
    except Exception as e:
         print(f"Failed Implicit Positional: {e}")

    try:
        rp = PublicKeyCredentialRpEntity(id="localhost", name="RoXX")
        print("Success: Kwargs")
    except Exception as e:
        print(f"Failed Kwargs: {e}")

    # Inspect the class
    import inspect
    print(f"Signature: {inspect.signature(PublicKeyCredentialRpEntity)}")

except Exception as e:
    print(f"General Error: {e}")

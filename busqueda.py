import boto3
import json
from botocore.exceptions import ClientError

def buscar_s3_public_access():
    # Inicializar el cliente de S3
    s3_client = boto3.client('s3')

    # Lista de buckets
    response = s3_client.list_buckets()
    buckets = response['Buckets']

    # Lista para almacenar los resultados
    resultados = []

    for bucket in buckets:
        bucket_name = bucket['Name']
        resultado = {}

        # Obtener estado de la política de bucket
        try:
            policy_status = s3_client.get_bucket_policy_status(Bucket=bucket_name)
            is_public_policy = policy_status['PolicyStatus']['IsPublic']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                is_public_policy = False
            elif e.response['Error']['Code'] == 'AccessDenied':
                is_public_policy = 'falta de permisos'
            else:
                is_public_policy = f'Error: {e.response["Error"]["Code"]}'

        # Obtener estado de la configuración ACL del bucket
        try:
            acl_grants = s3_client.get_bucket_acl(Bucket=bucket_name)
            grants = acl_grants['Grants']
            is_acl_public = any(grant['Grantee']['Type'] == 'Group' and
                                (grant['Grantee']['URI'] == 'http://acs.amazonaws.com/groups/global/AllUsers' or
                                 grant['Grantee']['URI'] == 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers')
                                for grant in grants)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                is_acl_public = 'falta de permisos'
            else:
                is_acl_public = f'Error: {e.response["Error"]["Code"]}'

        # Obtener configuración de cifrado de datos en reposo
        try:
            encryption_config = s3_client.get_bucket_encryption(Bucket=bucket_name)
            encryption_rules = encryption_config['ServerSideEncryptionConfiguration']['Rules']
            if encryption_rules:
                default_encryption = encryption_rules[0].get('ApplyServerSideEncryptionByDefault', {})
                sse_algorithm = default_encryption.get('SSEAlgorithm', 'None')
            else:
                sse_algorithm = 'None'
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                sse_algorithm = 'None'
            elif e.response['Error']['Code'] == 'AccessDenied':
                sse_algorithm = 'falta de permisos'
            else:
                sse_algorithm = f'Error: {e.response["Error"]["Code"]}'

        # Obtener estado del versionado de objetos del bucket y eliminación MFA
        try:
            versioning_status = s3_client.get_bucket_versioning(Bucket=bucket_name)
            if 'Status' in versioning_status:
                versioning_state = versioning_status['Status']
            else:
                versioning_state = 'No habilitado'

            if 'MFADelete' in versioning_status:
                mfa_delete = versioning_status['MFADelete']
            else:
                mfa_delete = 'No habilitado'
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                versioning_state = 'No habilitado'
                mfa_delete = 'No habilitado'
            elif e.response['Error']['Code'] == 'AccessDenied':
                versioning_state = 'falta de permisos'
                mfa_delete = 'falta de permisos'
            else:
                versioning_state = f'Error: {e.response["Error"]["Code"]}'
                mfa_delete = f'Error: {e.response["Error"]["Code"]}'

        # Obtener configuración de ciclo de vida del bucket
        try:
            lifecycle_config = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
            rules = lifecycle_config['Rules']
            if rules:
                lifecycle_state = 'Habilitado'
                lifecycle_rules = rules  # Puedes procesar esto más si necesitas detalles específicos
            else:
                lifecycle_state = 'No configurado'
                lifecycle_rules = []
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                lifecycle_state = 'No configurado'
                lifecycle_rules = []
            elif e.response['Error']['Code'] == 'AccessDenied':
                lifecycle_state = 'falta de permisos'
                lifecycle_rules = []
            else:
                lifecycle_state = f'Error: {e.response["Error"]["Code"]}'
                lifecycle_rules = []

        # Obtener estado de logging de acceso y modificaciones
        try:
            logging_status = s3_client.get_bucket_logging(Bucket=bucket_name)
            logging_enabled = logging_status.get('LoggingEnabled', None) is not None
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketLogging':
                logging_enabled = False
            elif e.response['Error']['Code'] == 'AccessDenied':
                logging_enabled = 'falta de permisos'
            else:
                logging_enabled = f'Error: {e.response["Error"]["Code"]}'

        # Determinar el estado NIST
        if sse_algorithm == 'None' or versioning_state == 'No habilitado':
            nist_state = 'FALL'
        else:
            nist_state = 'TRUE'

        # Almacenar resultados del bucket actual
        resultado['bucket'] = bucket_name
        resultado['is_public'] = is_public_policy
        resultado['is_acl_public'] = is_acl_public
        resultado['sse_algorithm'] = sse_algorithm
        resultado['versioning_state'] = versioning_state
        resultado['mfa_delete'] = mfa_delete  # Agregar estado MFA Delete
        resultado['lifecycle_state'] = lifecycle_state
        resultado['lifecycle_rules'] = lifecycle_rules
        resultado['nist_state'] = nist_state  # Agregar estado NIST
        resultado['logging_enabled'] = logging_enabled  # Agregar estado de logging

        resultados.append(resultado)

    # Devolver resultados en formato JSON
    return json.dumps(resultados)

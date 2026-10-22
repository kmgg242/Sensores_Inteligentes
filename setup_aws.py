import boto3
import os

REGION = "us-east-1"
COLLECTION_ID = "trabalhosensores_faces"

rekognition = boto3.client("rekognition", region_name=REGION)

def criar_colecao():
    try:
        rekognition.create_collection(CollectionId=COLLECTION_ID)
        print(f"Coleção '{COLLECTION_ID}' criada com sucesso!")
    except rekognition.exceptions.ResourceAlreadyExistsException:
        print(f"Coleção '{COLLECTION_ID}' já existe.")

def cadastrar_rosto(caminho_imagem, nome_pessoa):
    """
    nome_pessoa não pode conter espaços ou caracteres especiais na tag ExternalImageId.
    Use underline: ex. 'Kayke_Gregorio'
    """
    with open(caminho_imagem, "rb") as img_file:
        bytes_imagem = img_file.read()

    response = rekognition.index_faces(
        CollectionId=COLLECTION_ID,
        Image={"Bytes": bytes_imagem},
        ExternalImageId=nome_pessoa,
        DetectionAttributes=["ALL"],
        MaxFaces=1,
        QualityFilter="AUTO"
    )

    if response["FaceRecords"]:
        face_id = response["FaceRecords"][0]["Face"]["FaceId"]
        print(f"Rosto de '{nome_pessoa}' cadastrado! FaceId: {face_id}")
    else:
        print("Nenhum rosto detectado na imagem enviada.")

if __name__ == "__main__":
    criar_colecao()
    
    # Encontra automaticamente a pasta onde o setup_aws.py está guardado
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_foto = os.path.join(pasta_atual, "minha_foto.jpeg")
    
    cadastrar_rosto(caminho_foto, "Kayke_Gregorio")
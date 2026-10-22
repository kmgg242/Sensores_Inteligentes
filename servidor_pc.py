import serial
import cv2
import boto3
import json
import time
import os
from datetime import datetime

# Configurações da Porta Serial
PORTA_SERIAL = "COM10"
BAUD_RATE = 115200

# Configurações da AWS
REGION = "us-east-1"
COLLECTION_ID = "trabalhosensores_faces"
rekognition = boto3.client("rekognition", region_name=REGION)

# Diretórios e Arquivos
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_HISTORICO = os.path.join(PASTA_ATUAL, "capturas_historico")
os.makedirs(PASTA_HISTORICO, exist_ok=True)

ULTIMA_FOTO = os.path.join(PASTA_ATUAL, "ultima_captura.jpg")
ARQUIVO_STATUS = os.path.join(PASTA_ATUAL, "status.json")
ARQUIVO_HISTORICO = os.path.join(PASTA_ATUAL, "historico.json")

# Tradução de rótulos comuns da AWS para o painel
TRADUCAO_LABELS = {
    "Person": "Pessoa", "Human": "Humano", "Face": "Rosto", "Head": "Cabeça",
    "Clothing": "Vestuário", "Apparel": "Roupa", "Glasses": "Óculos",
    "Furniture": "Mobília", "Chair": "Cadeira", "Indoors": "Ambiente Interno",
    "Room": "Sala/Quarto", "Electronics": "Eletrônicos", "Screen": "Tela",
    "Monitor": "Monitor", "Computer": "Computador", "Wall": "Parede"
}

TRADUCAO_EMOCOES = {
    "HAPPY": "Feliz", "SAD": "Triste", "ANGRY": "Irritado",
    "CONFUSED": "Confuso", "DISGUSTED": "Descontente", "SURPRISED": "Surpreso",
    "CALM": "Calmo", "FEAR": "Assustado"
}

def salvar_evento(dados):
    # Salva o status atual
    with open(ARQUIVO_STATUS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    # Atualiza a lista de histórico (mantém os últimos 30 eventos)
    historico = []
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                historico = json.load(f)
        except Exception:
            historico = []

    historico.insert(0, dados)
    historico = historico[:30]

    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)

def desenhar_box(frame, bbox, texto, cor):
    altura, largura, _ = frame.shape
    x1 = int(bbox["Left"] * largura)
    y1 = int(bbox["Top"] * altura)
    x2 = int((bbox["Left"] + bbox["Width"]) * largura)
    y2 = int((bbox["Top"] + bbox["Height"]) * altura)

    # Retângulo principal
    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)

    # Tarja superior para o texto
    (w_texto, h_texto), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    y_tarja = max(y1 - 28, 0)
    cv2.rectangle(frame, (x1, y_tarja), (x1 + w_texto + 12, y_tarja + 28), cor, -1)
    cv2.putText(frame, texto, (x1 + 6, y_tarja + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def capturar_frame_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None

    for _ in range(5):
        cap.read()
        time.sleep(0.05)

    ret, frame = cap.read()
    cap.release()
    return frame if ret else None

def processar_captura():
    agora = datetime.now()
    horario = agora.strftime("%d/%m/%Y %H:%M:%S")
    id_arquivo = agora.strftime("%Y%m%d_%H%M%S")
    print(f"\n[{horario}] Gatilho PIR recebido! Analisando cena...")

    frame = capturar_frame_webcam()
    if frame is None:
        print("Erro: Falha ao acessar a webcam.")
        return

    # Salva o frame imediatamente para garantir atualização da imagem no painel
    cv2.imwrite(ULTIMA_FOTO, frame)

    # Codifica o frame em memória para enviar à AWS
    sucesso, buffer_jpg = cv2.imencode(".jpg", frame)
    if not sucesso:
        return
    bytes_imagem = buffer_jpg.tobytes()

    try:
        # 1. Verifica se há uma PESSOA na cena (mesmo sem rosto visível)
        resp_labels = rekognition.detect_labels(
            Image={"Bytes": bytes_imagem},
            MaxLabels=12,
            MinConfidence=70
        )

        labels_detectadas = []
        pessoa_detectada = False
        confianca_pessoa = 0.0
        boxes_pessoas = []

        for label in resp_labels.get("Labels", []):
            nome_en = label["Name"]
            nome_pt = TRADUCAO_LABELS.get(nome_en, nome_en)
            conf = round(label["Confidence"], 1)
            labels_detectadas.append(f"{nome_pt} ({conf}%)")

            if nome_en in ["Person", "Human"]:
                pessoa_detectada = True
                confianca_pessoa = max(confianca_pessoa, conf)
                for inst in label.get("Instances", []):
                    if "BoundingBox" in inst:
                        boxes_pessoas.append(inst["BoundingBox"])

        # 2. Detecta rostos e atributos biométricos de forma segura
        resp_faces = rekognition.detect_faces(
            Image={"Bytes": bytes_imagem},
            Attributes=["ALL"]
        )
        detalhes_rostos = resp_faces.get("FaceDetails", [])
        rosto_visivel = len(detalhes_rostos) > 0

        atributos_str = "Não disponível (rosto oculto)"
        box_rosto = None

        if rosto_visivel:
            face_principal = detalhes_rostos[0]
            box_rosto = face_principal.get("BoundingBox")
            
            # Leitura segura com .get() para evitar KeyError caso a AWS omita algum campo
            age_range = face_principal.get("AgeRange", {})
            idade_min = age_range.get("Low", "?")
            idade_max = age_range.get("High", "?")
            
            glasses_info = face_principal.get("Glasses", {})
            if "Value" in glasses_info:
                oculos = "Sim" if glasses_info["Value"] else "Não"
            else:
                # Verifica também se "Óculos" já foi detectado nos rótulos gerais da cena
                oculos = "Sim" if any("Óculos" in lbl for lbl in labels_detectadas) else "Não"
                
            emocoes = sorted(face_principal.get("Emotions", []), key=lambda x: x.get("Confidence", 0), reverse=True)
            emocao_top = TRADUCAO_EMOCOES.get(emocoes[0]["Type"], emocoes[0]["Type"]) if emocoes else "Neutra"
            
            if idade_min != "?":
                atributos_str = f"Idade est.: {idade_min}-{idade_max} anos | Expressão: {emocao_top} | Óculos: {oculos}"
            else:
                atributos_str = f"Rosto detectado | Expressão: {emocao_top} | Óculos: {oculos}"

        # 3. Classificação de Segurança (Autorizado vs Desconhecido vs Alarme Falso)
        if not pessoa_detectada and not rosto_visivel:
            resultado = {
                "timestamp": horario,
                "nivel_alerta": "AVISO",
                "status_seguranca": "ALARME FALSO (SEM HUMANOS)",
                "pessoa_detectada": False,
                "reconhecido": False,
                "pessoa": "Nenhuma pessoa na cena",
                "confianca": 0.0,
                "confianca_presenca": 0.0,
                "atributos": "Sem dados biométricos",
                "objetos_cena": labels_detectadas[:6],
                "mensagem": "O sensor de movimento disparou, mas nenhuma pessoa foi identificada na imagem."
            }

        elif rosto_visivel:
            # Procura o rosto na Collection de pessoas cadastradas
            resp_search = rekognition.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={"Bytes": bytes_imagem},
                MaxFaces=1,
                FaceMatchThreshold=80
            )
            matches = resp_search.get("FaceMatches", [])

            if matches:
                nome = matches[0]["Face"]["ExternalImageId"].replace("_", " ")
                similaridade = round(matches[0]["Similarity"], 2)
                desenhar_box(frame, box_rosto, f"AUTORIZADO: {nome} ({similaridade}%)", (40, 200, 40))

                resultado = {
                    "timestamp": horario,
                    "nivel_alerta": "SEGURO",
                    "status_seguranca": "ACESSO AUTORIZADO",
                    "pessoa_detectada": True,
                    "reconhecido": True,
                    "pessoa": nome,
                    "confianca": similaridade,
                    "confianca_presenca": confianca_pessoa or 99.9,
                    "atributos": atributos_str,
                    "objetos_cena": labels_detectadas[:6],
                    "mensagem": f"Identidade confirmada no banco de dados: {nome}."
                }
            else:
                desenhar_box(frame, box_rosto, "ALERTA: DESCONHECIDO", (0, 0, 235))

                resultado = {
                    "timestamp": horario,
                    "nivel_alerta": "CRITICO",
                    "status_seguranca": "INTRUSO / PESSOA DESCONHECIDA",
                    "pessoa_detectada": True,
                    "reconhecido": False,
                    "pessoa": "Indivíduo Não Cadastrado",
                    "confianca": 0.0,
                    "confianca_presenca": confianca_pessoa or 99.0,
                    "atributos": atributos_str,
                    "objetos_cena": labels_detectadas[:6],
                    "mensagem": "ALERTA DE SEGURANÇA: Pessoa detectada no perímetro sem cadastro no sistema!"
                }
        else:
            # Pessoa detectada (ex: de costas, longe ou rosto coberto), mas sem rosto visível para buscar
            for b_pes in boxes_pessoas:
                desenhar_box(frame, b_pes, f"INTRUSO (ROSTO OCULTO) {confianca_pessoa}%", (0, 0, 235))

            resultado = {
                "timestamp": horario,
                "nivel_alerta": "CRITICO",
                "status_seguranca": "INTRUSO (ROSTO NÃO VISÍVEL)",
                "pessoa_detectada": True,
                "reconhecido": False,
                "pessoa": "Desconhecido (Rosto Oculto/De Costas)",
                "confianca": 0.0,
                "confianca_presenca": confianca_pessoa,
                "atributos": atributos_str,
                "objetos_cena": labels_detectadas[:6],
                "mensagem": "ALERTA DE SEGURANÇA: Presença humana confirmada, mas o rosto não está visível!"
            }

        # Adiciona carimbo de data/hora estilo câmera de segurança no canto inferior da imagem
        cv2.putText(frame, f"CAM-01 | {horario} | {resultado['status_seguranca']}",
                    (15, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Salva a imagem anotada como última captura e guarda cópia no histórico
        caminho_evidencia = os.path.join(PASTA_HISTORICO, f"captura_{id_arquivo}.jpg")
        cv2.imwrite(ULTIMA_FOTO, frame)
        cv2.imwrite(caminho_evidencia, frame)
        resultado["arquivo_foto"] = caminho_evidencia

    except Exception as e:
        resultado = {
            "timestamp": horario,
            "nivel_alerta": "AVISO",
            "status_seguranca": "ERRO NO PROCESSAMENTO",
            "pessoa_detectada": False,
            "reconhecido": False,
            "pessoa": "Erro de API",
            "confianca": 0.0,
            "confianca_presenca": 0.0,
            "atributos": "-",
            "objetos_cena": [],
            "mensagem": f"Falha na comunicação com AWS: {str(e)}",
            "arquivo_foto": ULTIMA_FOTO
        }

    salvar_evento(resultado)
    print(f"--> [{resultado['nivel_alerta']}] {resultado['status_seguranca']}: {resultado['mensagem']}")

if __name__ == "__main__":
    print(f"Iniciando Central de Segurança na porta {PORTA_SERIAL}...")
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
        time.sleep(2)
        ser.reset_input_buffer()
        print(f"Monitoramento Ativo em {PORTA_SERIAL}! Aguardando sensores...\n")

        while True:
            if ser.in_waiting > 0:
                linha = ser.readline().decode("utf-8", errors="ignore").strip()
                if linha:
                    print(f"[SENSOR]: {linha}")
                if "TRIGGER_MOVIMENTO" in linha:
                    processar_captura()
            time.sleep(0.05)

    except serial.SerialException as e:
        print(f"\n[ERRO] Porta {PORTA_SERIAL} ocupada ou desconectada: {e}")
    except KeyboardInterrupt:
        print("\nCentral encerrada pelo operador.")
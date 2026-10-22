import streamlit as st
import json
import os
import time
from PIL import Image

st.set_page_config(
    page_title="Sentinela IoT | Videomonitoramento AWS",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ULTIMA_FOTO = os.path.join(PASTA_ATUAL, "ultima_captura.jpg")
ARQUIVO_STATUS = os.path.join(PASTA_ATUAL, "status.json")
ARQUIVO_HISTORICO = os.path.join(PASTA_ATUAL, "historico.json")

# Estilização CSS para visual de Central de Segurança (SOC)
st.markdown("""
<style>
    .banner-seguro {
        background: linear-gradient(90deg, #0f5132 0%, #198754 100%);
        color: white; padding: 18px 24px; border-radius: 10px;
        border-left: 8px solid #20c997; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .banner-critico {
        background: linear-gradient(90deg, #58151c 0%, #dc3545 100%);
        color: white; padding: 18px 24px; border-radius: 10px;
        border-left: 8px solid #ff6b6b; margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(220, 53, 69, 0.6);
        animation: pulse-red 1.5s infinite;
    }
    .banner-aviso {
        background: linear-gradient(90deg, #664d03 0%, #ffc107 100%);
        color: #111; padding: 18px 24px; border-radius: 10px;
        border-left: 8px solid #ffca2c; margin-bottom: 20px;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
        70% { box-shadow: 0 0 0 14px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    .tag-objeto {
        display: inline-block; background-color: #2b3035; color: #e9ecef;
        padding: 4px 10px; border-radius: 15px; font-size: 0.85rem;
        margin: 3px 4px 3px 0; border: 1px solid #495057;
    }
    .card-info {
        background-color: #1a1d20; padding: 15px; border-radius: 8px;
        border: 1px solid #343a40; margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Carregamento dos dados
status_atual = None
if os.path.exists(ARQUIVO_STATUS):
    try:
        with open(ARQUIVO_STATUS, "r", encoding="utf-8") as f:
            status_atual = json.load(f)
    except Exception:
        pass

historico = []
if os.path.exists(ARQUIVO_HISTORICO):
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            historico = json.load(f)
    except Exception:
        pass

# Barra Lateral de Controle
with st.sidebar:
    st.markdown("## 🛡️ Sentinela IoT")
    st.caption("Sistema Integrado ESP32 PIR + AWS Rekognition")
    st.divider()

    st.markdown("**Status dos Módulos:**")
    st.markdown("🟢 **Sensor PIR (ESP32):** Conectado (`COM10`)")
    st.markdown("🟢 **Motor IA:** AWS Rekognition")
    st.markdown("🟢 **Modo:** Vigilância Perimetral")
    st.divider()

    auto_refresh = st.toggle("Monitoramento em Tempo Real (2s)", value=True)
    alerta_sonoro = st.toggle("Alarme Sonoro para Intrusos", value=False)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()
    with col_b2:
        if st.button("🗑️ Limpar Log", use_container_width=True):
            if os.path.exists(ARQUIVO_HISTORICO):
                os.remove(ARQUIVO_HISTORICO)
            if os.path.exists(ARQUIVO_STATUS):
                os.remove(ARQUIVO_STATUS)
            st.rerun()

# Cabeçalho e KPIs
st.markdown("## 📹 Central de Monitoramento e Controle de Acesso")

total_eventos = len(historico)
total_autorizados = sum(1 for h in historico if h.get("nivel_alerta") == "SEGURO")
total_intrusos = sum(1 for h in historico if h.get("nivel_alerta") == "CRITICO")
total_falsos = sum(1 for h in historico if h.get("nivel_alerta") == "AVISO")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total de Disparos PIR", total_eventos)
kpi2.metric("Acessos Autorizados", total_autorizados)
kpi3.metric("Alertas de Intrusos", total_intrusos, delta="Atenção" if total_intrusos > 0 else None, delta_color="inverse")
kpi4.metric("Alarmes Falsos (Sem Pessoas)", total_falsos)

st.divider()

# Banner Principal de Alerta
if status_atual:
    nivel = status_atual.get("nivel_alerta", "AVISO")
    titulo_status = status_atual.get("status_seguranca", "EVENTO DETECTADO")
    msg_status = status_atual.get("mensagem", "")
    hora_status = status_atual.get("timestamp", "")

    if nivel == "CRITICO":
        st.markdown(f"""
        <div class="banner-critico">
            <h2 style="margin:0; color:white;">🚨 ALERTA DE SEGURANÇA: {titulo_status}</h2>
            <p style="margin:6px 0 0 0; font-size:1.1rem;"><b>{hora_status}</b> — {msg_status}</p>
        </div>
        """, unsafe_allow_html=True)
        if alerta_sonoro:
            st.markdown(
                '<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg"></audio>',
                unsafe_allow_html=True
            )
    elif nivel == "SEGURO":
        st.markdown(f"""
        <div class="banner-seguro">
            <h2 style="margin:0; color:white;">✅ {titulo_status}: {status_atual.get('pessoa')}</h2>
            <p style="margin:6px 0 0 0; font-size:1.1rem;"><b>{hora_status}</b> — {msg_status}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="banner-aviso">
            <h3 style="margin:0; color:#111;">⚠️ {titulo_status}</h3>
            <p style="margin:6px 0 0 0;"><b>{hora_status}</b> — {msg_status}</p>
        </div>
        """, unsafe_allow_html=True)

    # Painel Central: Câmera + Telemetria Biométrica
    col_cam, col_dados = st.columns([1.35, 1])

    with col_cam:
        st.markdown("#### 📸 Feed da Câmera de Segurança (CAM-01)")
        if os.path.exists(ULTIMA_FOTO):
            img = Image.open(ULTIMA_FOTO)
            st.image(img, use_container_width=True)
        else:
            st.info("Nenhuma imagem capturada até o momento.")

    with col_dados:
        st.markdown("#### 🔍 Dossiê de Inspeção Visual (AWS Rekognition)")

        st.markdown(f"""
        <div class="card-info">
            <b>👤 Identificação:</b> {status_atual.get('pessoa', '-')}<br>
            <b>🕒 Horário do Disparo:</b> {status_atual.get('timestamp', '-')}<br>
            <b>🧬 Análise Biométrica:</b> {status_atual.get('atributos', 'Não aplicável')}
        </div>
        """, unsafe_allow_html=True)

        conf_presenca = float(status_atual.get("confianca_presenca", 0.0))
        st.write(f"**Confiança de Presença Humana na Cena:** `{conf_presenca}%`")
        st.progress(min(int(conf_presenca), 100))

        conf_id = float(status_atual.get("confianca", 0.0))
        st.write(f"**Similaridade com Banco de Pessoas Autorizadas:** `{conf_id}%`")
        st.progress(min(int(conf_id), 100))

        st.markdown("**🏷️ Elementos e Objetos Detectados no Perímetro:**")
        objetos = status_atual.get("objetos_cena", [])
        if objetos:
            tags_html = "".join([f'<span class="tag-objeto">{obj}</span>' for obj in objetos])
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.caption("Nenhum objeto relevante listado.")

else:
    st.info("🛡️ Sistema pronto e em vigília. Aguardando o primeiro disparo do sensor de movimento...")

st.divider()

# Registro de Auditoria e Galeria de Evidências
st.markdown("### 📋 Registro de Ocorrências Recentes")
if historico:
    col_tabela, col_galeria = st.columns([1.4, 1])

    with col_tabela:
        linhas_tabela = []
        for item in historico:
            icone = "🚨" if item.get("nivel_alerta") == "CRITICO" else ("✅" if item.get("nivel_alerta") == "SEGURO" else "⚠️")
            linhas_tabela.append({
                "Alerta": f"{icone} {item.get('status_seguranca', '')}",
                "Horário": item.get("timestamp", ""),
                "Indivíduo": item.get("pessoa", ""),
                "Biometria": item.get("atributos", ""),
                "Similaridade": f"{item.get('confianca', 0)}%"
            })
        st.dataframe(linhas_tabela, use_container_width=True, hide_index=True)

    with col_galeria:
        st.markdown("**🖼️ Galeria de Capturas Anteriores**")
        opcoes = [f"{i+1}. [{h.get('timestamp')}] {h.get('status_seguranca')} - {h.get('pessoa')}" for i, h in enumerate(historico)]
        selecao = st.selectbox("Inspecionar evidência gravada:", opcoes)
        idx = opcoes.index(selecao)
        caminho_foto_hist = historico[idx].get("arquivo_foto")
        if caminho_foto_hist and os.path.exists(caminho_foto_hist):
            st.image(Image.open(caminho_foto_hist), use_container_width=True)
else:
    st.caption("Nenhum evento registrado no histórico ainda.")

if auto_refresh:
    time.sleep(2)
    st.rerun()
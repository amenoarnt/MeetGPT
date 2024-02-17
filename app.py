
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from pathlib import Path
from datetime import datetime
import time
import queue
import pydub
from dotenv import load_dotenv, find_dotenv
import openai
import os

_ = load_dotenv(find_dotenv())


openai.api_key = os.getenv('OPENAI_API_KEY')


PASTA_ARQUIVOS = Path(__file__).parent / 'arquivos'
PASTA_ARQUIVOS.mkdir(exist_ok=True)

# PROMPT = f'Te providenciarei a transcrição de uma reunião e a sua tarefa é fazer um resumo da reunião na formatação a seguir:
# \n    \n    -Resumo da reunião\n    
# -Action items (o que precisa ser feito e quem é o responsável por fazê-lo)\n    
# -Se aplicável, uma lista de tópicos a serem discutuidos nas próximas reuniões."'

PROMPT = '''
Te providenciarei a transcrição de uma reunião e a sua tarefa é fazer um resumo da reunião.
Inicialmente, você deve identificar os participantes da reunião, caso não seja possível identificar algum participante, você deve identificá-lo pelo sexo e atribuir um número para ele. Por exemplo: "Participante Masculino 1" ou "Participante Feminino 1";
O resumo deve ser detalhado e conter os principais pontos discutidos.
O resumo deve ter no máximo 500 caracteres.
O resumo deve estar em texto corrido. 
Em seguida, devem ser apresentados todos acordos e combinados feitos na reunião no formato de bullet points.
No final, devem ser apresentadas as ações (action items) que devem ser tomadas após a reunião, com a indicação do responsável.

O formato do texto que eu desejo é o seguinte:
**Participantes**:
- Nome do participante 1 (caso não seja possível identificar o nome do participante, identificar pelo sexo e atribuir um número para ele. Por exemplo: "Participante Masculino 1" ou "Participante Feminino 1")
- Nome do participante 2 (caso não seja possível identificar o nome do participante, identificar pelo sexo e atribuir um número para ele. Por exemplo: "Participante Masculino 2" ou "Participante Feminino 2")
- Nome do participante 3 (caso não seja possível identificar o nome do participante, identificar pelo sexo e atribuir um número para ele. Por exemplo: "Participante Masculino 3" ou "Participante Feminino 3")
- Nome do participante n (caso não seja possível identificar o nome do participante, identificar pelo sexo e atribuir um número para ele. Por exemplo: "Participante Masculino n" ou "Participante Feminino n")

**Resumo da reunião**:
- escrever aqui o resumo

**Acordos da reunião**: 
- acordo 1 
- acordo 2 
- acordo 3 
- acordo n

**Action items da reunião**:
- ação 1 (responsável)
- ação 2 (responsável)
- ação 3 (responsável)
- ação n (responsável)
'''

client = openai.OpenAI()

def salva_arquivo(caminho_do_arquivo, conteudo):
    with open (caminho_do_arquivo, 'w') as f:
        f.write(conteudo)


def le_arquivo(caminho_arquivo):
    if caminho_arquivo.exists():
        with open (caminho_arquivo) as f:
            return f.read()
    else:
        return ''
    

def listar_reunioes():
    lista_reunioes = PASTA_ARQUIVOS.glob('*')
    lista_reunioes = list(lista_reunioes)
    lista_reunioes.sort(reverse=True)
    reunioes_dict = {}
    for pasta_reuniao in lista_reunioes:
        data_reuniao = pasta_reuniao.stem
        ano, mes, dia, hora, min, seg = data_reuniao.split('_')
        reunioes_dict[data_reuniao] = f'{dia}/{mes}/{ano} {hora}:{min}:{seg}'
        titulo = le_arquivo(pasta_reuniao / 'titulo.txt')
        if titulo != '':
            reunioes_dict[data_reuniao] += f' - {titulo}'
    return reunioes_dict


# ________________ OPENAI UTILS ________________

def transcreve_audio(caminho_audio, language='pt', response_format='text'):
    with open(caminho_audio, 'rb') as arquivo_audio: 
        transcricao = client.audio.transcriptions.create(
            model='whisper-1',
            file=arquivo_audio,
            language=language,
            response_format=response_format
        )
        return transcricao
    
def chat_openai(
        mensagens,
        modelo='gpt-3.5-turbo-1106',
        temperatura=0,
        stream=False
):
    resposta = client.chat.completions.create(
        model=modelo,
        messages=mensagens,
        temperature=temperatura,
        stream=stream
    )
    return resposta.choices[0].message.content


# ________________ STREAMLIT APP ________________


# --------- TAB GRAVAR REUNIAO ---------

def adiciona_chunk_audio(frames_de_audio, audio_chunk):
    for frame in frames_de_audio: 
        sound = pydub.AudioSegment(
            data=frame.to_ndarray().tobytes(),
            sample_width=frame.format.bytes,
            frame_rate=frame.sample_rate,
            channels=len(frame.layout.channels),
        )
        audio_chunk += sound
    return audio_chunk

def tab_gravar_reuniao():
    st.markdown('## Upload de arquivo de áudio')
    uploaded_file = st.file_uploader('Selecione um arquivo de áudio', type=['mp3', 'wav', 'ogg', 'flac'])

    if uploaded_file is not None:
        # Initialize or get the current uploaded file name in session state
        current_file_name = st.session_state.get('uploaded_file_name', '')
        
        # Check if the current uploaded file has been processed already
        if uploaded_file.name != current_file_name:
            # Update the session state with the new file name
            st.session_state['uploaded_file_name'] = uploaded_file.name
            
            pasta_arquivo = PASTA_ARQUIVOS / datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            if not pasta_arquivo.exists():
                pasta_arquivo.mkdir(parents=True, exist_ok=True)
            file_path = pasta_arquivo / uploaded_file.name

            # Write the uploaded file to the new path
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())
            st.success('Arquivo salvo com sucesso: {}'.format(file_path))

            # Process the file as needed (e.g., transcription)
            transcricao_resultado = transcreve_audio(file_path)
            salva_arquivo(pasta_arquivo / 'transcricao.txt', transcricao_resultado)
        else:
            st.info('Arquivo já processado.')


    # st.markdown('## Gravar reunião')
    # st.markdown('Clique no botão para começar a gravar')
    # st.markdown('A gravação será salva automaticamente ao fim da reunião')
    # webrtx_ctx = webrtc_streamer(
    #     key="recebe_audio",
    #     mode=WebRtcMode.SENDONLY,
    #     audio_receiver_size=1024,
    #     media_stream_constraints={'video': False, 'audio': True},
    # )

    # if not webrtx_ctx.state.playing:
    #     st.markdown("Comece a falar!")
    #     return

    # container  = st.empty()
    # container.markdown('Estou captando áudio...')
    # pasta_reuniao = PASTA_ARQUIVOS / datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    # pasta_reuniao.mkdir()

    # ultima_transcricao = time.time()
    # audio_completo = pydub.AudioSegment.empty()
    # audio_chunk = pydub.AudioSegment.empty()
    # transcricao = ''

    # while True: 
    #     if webrtx_ctx.audio_receiver:
    #         try: 
    #             frames_de_audio = webrtx_ctx.audio_receiver.get_frames(timeout=1)
    #         except queue.Empty:
    #             time.sleep(0.1)
    #             continue
    #         audio_completo = adiciona_chunk_audio(frames_de_audio, audio_completo)
    #         audio_chunk = adiciona_chunk_audio(frames_de_audio, audio_chunk)
    #         if len(audio_chunk) > 0:
    #             audio_completo.export(pasta_reuniao /'audio.mp3')
    #             agora = time.time()
    #             if agora - ultima_transcricao > 5: 
    #                 ultima_transcricao = agora
    #                 audio_chunk.export(pasta_reuniao / 'audio_temp.mp3')
    #                 transcricao_chunk = transcreve_audio(pasta_reuniao / 'audio_temp.mp3')
    #                 transcricao += transcricao_chunk
    #                 salva_arquivo(pasta_reuniao / 'transcricao.txt', transcricao)
    #                 container.markdown(transcricao)

    #                 audio_chunk = pydub.AudioSegment.empty()

    #     else: 
    #         break



# --------- TAB SELEÇÃO REUNIAO ---------

def tab_selecao_reuniao():
    reunioes_dict = listar_reunioes()

    if len(reunioes_dict) > 0:
        reuniao_selecionada = st.selectbox('Selecione uma reunião', 
                                       list(reunioes_dict.values()))
        st.divider()
        reuniao_data = [key for key, value in reunioes_dict.items() if value == reuniao_selecionada][0]
        pasta_reuniao = PASTA_ARQUIVOS / reuniao_data
        if not (pasta_reuniao / 'titulo.txt').exists():
            st.warning('Adicione título à reunião')
            titulo_reuniao = st.text_input('Título da reunião')
            st.button('Salvar', 
                      on_click=salvar_titulo,
                      args=(pasta_reuniao, titulo_reuniao))
        else:
            titulo = le_arquivo(pasta_reuniao / 'titulo.txt')
            transcricao = le_arquivo(pasta_reuniao / 'transcricao.txt')
            resumo = le_arquivo(pasta_reuniao / 'resumo.txt')
            audio_file = open(pasta_reuniao / 'audio.mp3', 'rb')
            audio_bytes = audio_file.read()
            if resumo == '':
                gerar_resumo(pasta_reuniao)
            st.markdown(f'## {titulo} ##')
            st.markdown(f'{resumo}')
            st.markdown('### Transcrição ###')
            st.markdown(transcricao)
            st.markdown('### Gravação ###')
            st.audio(audio_bytes)





def salvar_titulo(pasta_reuniao, titulo):
    salva_arquivo(pasta_reuniao / 'titulo.txt', titulo)


def gerar_resumo(pasta_reuniao):
    transcricao = le_arquivo(pasta_reuniao / 'transcricao.txt')
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": "####{}####".format(transcricao)}
    ]
    resumo = chat_openai(mensagens=messages)
    salva_arquivo(pasta_reuniao / 'resumo.txt', resumo)

# --------- MAIN---------

def main():
    st.header('Bem vindo ao MeetGPT', divider=True)
    tab_gravar, tab_selecao = st.tabs(['Gravar reunião', 'Ver transcrições salvas'])
    with tab_gravar:
        tab_gravar_reuniao()
    with tab_selecao:
        tab_selecao_reuniao()


if __name__ == '__main__':
    main()
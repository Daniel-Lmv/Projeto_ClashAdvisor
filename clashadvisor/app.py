"""Interface Streamlit, com conversas independentes por thread_id."""
import asyncio
import uuid
from pathlib import Path
import streamlit as st
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from clashadvisor.graph import build_graph
from clashadvisor.config import ROOT
from clashadvisor.memory import add_message, recent_messages

st.set_page_config(page_title='ClashAdvisor', page_icon='🏰')
st.title('ClashAdvisor')
st.caption('Orientação para Clash of Clans com documentos, ferramentas e memória por conversa.')
if 'session_id' not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if 'messages' not in st.session_state:
    st.session_state.messages = recent_messages(st.session_state.session_id)

with st.sidebar:
    st.subheader('Conversa')
    st.caption('Cada conversa recebe um identificador independente.')
    if st.button('Nova conversa', use_container_width=True):
        st.session_state.session_id = uuid.uuid4().hex
        st.session_state.messages = []
        st.rerun()
    st.caption('ID atual: ' + st.session_state.session_id)
    resume_id = st.text_input('Retomar conversa pelo ID', placeholder='Cole o identificador completo')
    if st.button('Retomar conversa', use_container_width=True):
        if resume_id.strip() and len(resume_id.strip()) <= 80:
            st.session_state.session_id = resume_id.strip()
            st.session_state.messages = recent_messages(resume_id.strip())
            st.rerun()
        else:
            st.warning('Informe um ID de conversa válido.')
    st.divider()
    st.caption('O MCP próprio precisa estar ligado na porta definida no .env.')

for item in st.session_state.messages:
    with st.chat_message(item['role']):
        st.markdown(item['content'])
        if item.get('ferramenta') or item.get('skills'):
            st.caption('Ferramenta: ' + (item.get('ferramenta') or 'nenhuma'))
            st.caption('Skills: ' + (', '.join(item.get('skills') or []) or 'nenhuma'))


async def run_turn(question: str, thread_id: str) -> dict:
    # A conexão é aberta apenas durante a execução e salva checkpoints no disco.
    db = str(ROOT / 'clashadvisor_checkpoints.sqlite')
    async with AsyncSqliteSaver.from_conn_string(db) as saver:
        graph = build_graph(checkpointer=saver)
        return await graph.ainvoke(
            {'pergunta': question, 'session_id': thread_id},
            config={'configurable': {'thread_id': thread_id}},
        )


question = st.chat_input('Pergunte sobre sua vila, melhorias ou estratégias')
if question:
    with st.chat_message('user'):
        st.markdown(question)
    st.session_state.messages.append({'role': 'user', 'content': question})
    add_message(st.session_state.session_id, 'user', question)
    with st.chat_message('assistant'):
        with st.spinner('Consultando...'):
            try:
                state = asyncio.run(run_turn(question, st.session_state.session_id))
                response = state.get('resposta') or 'Não foi possível gerar uma resposta.'
                used_tool = state.get('ferramenta') or ''
                used_skills = state.get('skills_carregadas') or []
                st.markdown(response)
                st.caption('Ferramenta: ' + (used_tool or 'nenhuma'))
                st.caption('Skills: ' + (', '.join(used_skills) or 'nenhuma'))
                if state.get('fontes'):
                    st.caption('Fontes: ' + ', '.join(state['fontes']))
            except Exception as exc:
                response = 'Não foi possível executar esta pergunta: ' + str(exc)
                used_tool, used_skills = '', []
                st.error(response)
    st.session_state.messages.append({'role': 'assistant', 'content': response,
                                      'ferramenta': used_tool, 'skills': used_skills})
    add_message(st.session_state.session_id, 'assistant', response)

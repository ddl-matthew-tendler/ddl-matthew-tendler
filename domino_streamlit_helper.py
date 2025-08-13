import streamlit as st
from domino import Domino

st.title('Domino Streamlit App Creator')
st.write('This app helps you scaffold and publish new Domino apps.')

st.header('App Details')
new_app_name = st.text_input('New app name', value='')
new_app_description = st.text_area('Description', value='')

st.header('Execution Settings')
env_id = st.text_input('Environment ID')
hardware_tier_id = st.text_input('Hardware Tier ID')

if st.button('Publish'):
    if not new_app_name or not env_id or not hardware_tier_id:
        st.error('Please provide app name, environment ID and hardware tier ID.')
    else:
        # Create a Domino client using credentials available in the Domino workspace
        domino = Domino('domino_streamlit_helper', api_key=None, host=None)
        try:
            domino.app_publish(hardwareTierId=hardware_tier_id)
            st.success('Published app ' + new_app_name)
        except Exception as e:
            st.error(f'Failed to publish: {e}')
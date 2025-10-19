#!/usr/bin/env python

import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()

from functions.ospf_isis_mcp import ospf_isis_mcp_main

SCENARIOS = {
    "OSPF/IS-IS Network AI Assistant": ospf_isis_mcp_main,
}


def main() -> None:
    st.set_page_config(layout="wide")

    page = st.sidebar.radio("Choose scenario:", list(SCENARIOS.keys()))
    SCENARIOS[page]()


if __name__ == "__main__":
    main()
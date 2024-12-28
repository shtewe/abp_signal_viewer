# main.py

import sys
import logging
import os
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

from models.abp_model import ABPModel
from views.main_view import MainView
from controllers.main_controller import MainController

def setup_logging():
    log_level = os.getenv("LOG_LEVEL","DEBUG").upper()
    numeric_level = getattr(logging, log_level, logging.DEBUG)
    logging.basicConfig(
        filename='abp_signal_viewer.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=numeric_level
    )
    logging.info("Logging is set up.")

def main():
    load_dotenv()
    setup_logging()
    logging.info("App started.")

    app = QApplication(sys.argv)

    model = ABPModel(
        database_name=os.getenv("DATABASE_NAME","mimic3wdb-matched"),
        data_dir=os.getenv("DATA_DIR","./data")
    )
    view = MainView()
    controller = MainController(view, model)

    # Optional: load a stylesheet
    stylesheet_path = os.path.join(os.path.dirname(__file__),'resources','styles','styles.qss')
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path,'r') as f:
            app.setStyleSheet(f.read())
    else:
        logging.warning(f"No stylesheet found at {stylesheet_path}.")

    view.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()

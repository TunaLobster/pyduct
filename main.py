# MAE 3403 PyDuct Design Project
# 5/5/17
# Charlie Johnson
# Nick Nelsen
# Stephen Ziske

# github.com/TunaLobster/pyduct

import sys

from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtWidgets import QFileDialog

from pyduct import calculate
from pyduct_ui import Ui_Dialog


class main_window(QDialog):
    def __init__(self):
        super(main_window, self).__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.assign_widgets()
        self.show()

    # Setup Callbacks for all buttons or other clickable devices
    def assign_widgets(self):
        self.ui.pushButton.clicked.connect(self.getFileName)
        self.ui.buttonBox.accepted.connect(self.runPyduct)
        self.ui.buttonBox.rejected.connect(self.ExitApp)

    def getFileName(self):  # Get file from user
        filename = QFileDialog.getOpenFileName()
        self.ui.lineEdit.setText(str(filename[0]))

    def runPyduct(self):
        print('Running...')  # Says the program is running
        calculate(str(self.ui.lineEdit.text()))  # Runs pyduct.py and gets all the values, then prints them

    def ExitApp(self):
        app.exit()


if __name__ == "__main__":
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        app.aboutToQuit.connect(app.deleteLater)
    main_win = main_window()
    app.exec_()

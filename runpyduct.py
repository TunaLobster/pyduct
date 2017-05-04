from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtWidgets import QFileDialog
import sys
from pyduct_ui import Ui_Dialog
from pyduct import calculate

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

    def getFileName(self):
        filename = QFileDialog.getOpenFileName()
        self.ui.lineEdit.setText(str(filename[0]))

    def runPyduct(self):
        calculate(str(self.ui.lineEdit.text()))

    def ExitApp(self):
        app.exit()


if __name__ == "__main__":
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        app.aboutToQuit.connect(app.deleteLater)
    main_win = main_window()
    app.exec_()
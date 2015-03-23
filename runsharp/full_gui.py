import sys, os
import numpy as np

if len(sys.argv) > 1 and sys.argv[1] == '--debug':
    sys.path.insert(0, os.path.normpath(os.getcwd() + "/.."))
else:
    np.seterr(all='ignore')

from sharppy.viz import SkewApp, MapWidget 
import sharppy.sharptab.profile as profile
from sharppy.io.buf_decoder import BufkitFile
from datasources import data_source

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import *
import datetime as date
from StringIO import StringIO
import urllib

class DataThread(QThread):
    progress = Signal()
    def __init__(self, parent, **kwargs):
        super(DataThread, self).__init__(parent)
        self.model = kwargs.get("model")
        self.runtime = kwargs.get("run")
        self.loc = kwargs.get("loc")
        self.prof_idx = kwargs.get("idx")
        self.profs = []
        self.d = None
        self.exc = ""

    def returnData(self):
        if self.exc == "":
            return self.profs, self.d
        else:
            return self.exc

    def make_profile(self, i):
        d = self.d
        prof = profile.create_profile(profile='convective', hght = d.hght[0][i],
                tmpc = d.tmpc[0][i], dwpc = d.dwpc[0][i], pres = d.pres[0][i],
                wspd=d.wspd[0][i], wdir=d.wdir[0][i])
        return prof

    def __modelProf(self):
        if self.model == "GFS":
            d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/' + self.model + '/' + self.runtime[:-1] + '/'
                + self.model.lower() + '3_' + self.loc.lower() + '.buf')
        elif self.model.startswith("NAM") and (self.runtime.startswith("06") or self.runtime.startswith("18")):
            d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/' + self.model + '/' + self.runtime[:-1] + '/'
                + self.model.lower() + 'm_' + self.loc.lower() + '.buf')
        else:
            d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/' + self.model + '/' + self.runtime[:-1] + '/'
                + self.model.lower() + '_' + self.loc.lower() + '.buf')
        self.d = d

        if self.model == "SREF":
            for i in self.prof_idx:
                profs = []
                for j in range(len(d.wdir)):
                    ##print "MAKING PROFILE OBJECT: " + datetime.strftime(d.dates[i], '%Y%m%d/%H%M')
                    if j == 0:
                        profs.append(profile.create_profile(profile='convective', omeg = d.omeg[j][i], hght = d.hght[j][i],
                        tmpc = d.tmpc[j][i], dwpc = d.dwpc[j][i], pres = d.pres[j][i], wspd=d.wspd[j][i], wdir=d.wdir[j][i]))
                        self.progress.emit()
                    else:
                        profs.append(profile.create_profile(profile='default', omeg = d.omeg[j][i], hght = d.hght[j][i],
                        tmpc = d.tmpc[j][i], dwpc = d.dwpc[j][i], pres = d.pres[j][i], wspd=d.wspd[j][i], wdir=d.wdir[j][i]))
                self.profs.append(profs)

        else:
            for i in self.prof_idx:
                ##print "MAKING PROFILE OBJECT: " + date.datetime.strftime(d.dates[i], '%Y%m%d/%H%M')
                self.profs.append(profile.create_profile(profile='convective', omeg = d.omeg[0][i], hght = d.hght[0][i],
                    tmpc = d.tmpc[0][i], dwpc = d.dwpc[0][i], pres = d.pres[0][i], wspd=d.wspd[0][i], wdir=d.wdir[0][i]))
                self.progress.emit()

    def run(self):
        try:
            self.__modelProf()
        except Exception as e:
            self.exc = str(e)

# Create an application
app = QApplication([])

class MainWindow(QWidget):
    date_format = "%Y-%m-%d %HZ"
    run_format = "%d %B %Y / %H%M UTC"

    def __init__(self, **kwargs):
        """
        Construct the main window and handle all of the
        necessary events. This window serves as the SHARPpy
        sounding picker - a means for interactively selecting
        which sounding profile(s) to view.
        """

        super(MainWindow, self).__init__(**kwargs)
        self.progressDialog = QProgressDialog()
        self.data_sources = data_source.loadDataSources()

        ## All of these variables get set/reset by the various menus in the GUI

        ## this is the time step between available profiles
        self.delta = 12
        ## default the sounding location to OUN because obviously I'm biased
        self.loc = "OUN"
        ## set the default profile to display
        self.prof_time = "Latest"
        ## the index of the item in the list that corresponds
        ## to the profile selected from the list
        self.prof_idx = []
        ## set the default profile type to Observed
        self.model = "Observed"
        ## the delay is time time delay between sounding availabilities for models
        self.delay = 1
        ## Offset in time from the synoptic hours
        self.offset = 0
        ## this is the duration of the period the available profiles have
        self.duration = 17
        ## this is the default model initialization time.
        self.run = [ t for t in self.data_sources[self.model].getAvailableTimes() if t.hour in [0, 12] ][-1]
        ## this is the default map to display
        self.map = None
        ## initialize the UI
        self.__initUI()

    def __initUI(self):
        """
        Initialize the main user interface.
        """

        ## Give the main window a layout. Using GridLayout
        ## in order to control placement of objects.

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        ## set the window title
        self.setWindowTitle('SHARPpy Sounding Picker')

        # Create and fill a QWebView
        self.view = self.create_map_view()
        self.button = QPushButton('Generate Profiles')
        self.button.clicked.connect(self.complete_name)
        self.select_flag = False
        self.all_profs = QPushButton("Select All")
        self.all_profs.clicked.connect(self.select_all)
        self.all_profs.setDisabled(True)

        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.profile_list.setDisabled(True)

        ## create subwidgets that will hold the individual GUI items
        self.left_data_frame = QWidget()
        self.right_map_frame = QWidget()
        ## set the layouts for these widgets
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        self.left_data_frame.setLayout(self.left_layout)
        self.right_map_frame.setLayout(self.right_layout)

        ## create dropdown menus
        models = sorted(self.data_sources.keys())
        self.model_dropdown = self.dropdown_menu(models) #['Observed', 'GFS', 'NAM', 'NAM4KM', 'RAP', 'HRRR', 'SREF'])
        self.model_dropdown.setCurrentIndex(models.index(self.model))
        self.map_dropdown = self.dropdown_menu(['CONUS', 'Southeast', 'Central', 'West', 'Northeast', 'Europe', 'Asia'])
        times = self.data_sources[self.model].getAvailableTimes()
        self.run_dropdown = self.dropdown_menu([ t.strftime(MainWindow.run_format) for t in times ])
        self.run_dropdown.setCurrentIndex(times.index(self.run))

        ## connect the click actions to functions that do stuff
        self.model_dropdown.activated.connect(self.get_model)
        self.map_dropdown.activated.connect(self.get_map)
        self.run_dropdown.activated.connect(self.get_run)

        ## Create text labels to describe the various menus
        self.type_label = QLabel("Select Sounding Source")
        self.date_label = QLabel("Select Forecast Time")
        self.map_label = QLabel("Select Map Area")
        self.run_label = QLabel("Select Cycle")
        self.date_label.setDisabled(True)

        ## add the elements to the left side of the GUI
        self.left_layout.addWidget(self.type_label)
        self.left_layout.addWidget(self.model_dropdown)
        self.left_layout.addWidget(self.run_label)
        self.left_layout.addWidget(self.run_dropdown)
        self.left_layout.addWidget(self.date_label)
        self.left_layout.addWidget(self.profile_list)
        self.left_layout.addWidget(self.all_profs)
        self.left_layout.addWidget(self.button)

        ## add the elements to the right side of the GUI
        self.right_layout.addWidget(self.map_label)
        self.right_layout.addWidget(self.map_dropdown)
        self.right_layout.addWidget(self.view)

        ## add the left and right sides to the main window
        self.layout.addWidget(self.left_data_frame, 0, 0, 1, 1)
        self.layout.addWidget(self.right_map_frame, 0, 1, 1, 1)
        self.left_data_frame.setMaximumWidth(280)

        self.menuBar()

    def __date(self):
        """
        This function does some date magic to get the current date nearest to 00Z or 12Z
        """
        current_time = date.datetime.utcnow()
        delta = date.timedelta(hours=12)
        today_00Z = date.datetime.strptime( str(current_time.year) + str(current_time.month).zfill(2) +
                                            str(current_time.day).zfill(2) + "00", "%Y%m%d%H")
        if current_time.hour >= 12:
            time = today_00Z + delta
        else:
            time = today_00Z

        return time

    def menuBar(self):

        self.bar = QMenuBar()
        self.filemenu = self.bar.addMenu("File")

        opendata = QAction("Open", self, shortcut=QKeySequence("Ctrl+O"))
        opendata.triggered.connect(self.openFile)
        self.filemenu.addAction(opendata)

        exit = QAction("Exit", self, shortcut=QKeySequence("Ctrl+Q"))
        exit.triggered.connect(self.exitApp)        
        self.filemenu.addAction(exit)

        pref = QAction("Preferences", self)
        self.filemenu.addAction(pref)

        self.helpmenu = self.bar.addMenu("Help")

        about = QAction("About", self)
        about.triggered.connect(self.aboutbox)

        self.helpmenu.addAction(about)

    def exitApp(self):
        self.close()

    def openFile(self):
        self.link, _ = QFileDialog.getOpenFileName(self, 'Open file', '/home')
        self.model = "Archive"
        self.location = None
        self.prof_time = None
        self.run = None

        self.skewApp()

        ## this is the time step between available profiles
        self.delta = 12
        ## default the sounding location to OUN because obviously I'm biased
        self.loc = "OUN"
        ## set the default profile to display
        self.prof_time = "Latest"
        ## the index of the item in the list that corresponds
        ## to the profile selected from the list
        self.prof_idx = []
        ## set the default profile type to Observed
        self.model = "Observed"
        ## the delay is time time delay between sounding availabilities for models
        self.delay = 1
        ## Offset time from the synoptic hour
        self.offset = 0
        ## this is the duration of the period the available profiles have
        self.duration = 17
        ## this is the default model initialization time.
        self.run = "00Z"
        ## this is the default map to display
        self.map = None

    def aboutbox(self):

        cur_year = date.datetime.utcnow().year
        msgBox = QMessageBox()
        msgBox.setText("SHARPpy\nSounding and Hodograph Research and Analysis Program for " +
                       "Python\n\n(C) 2014-%d by Kelton Halbert and Greg Blumberg" % cur_year)
        msgBox.exec_()

    def create_map_view(self):
        """
        Create a clickable map that will be displayed in the GUI.
        Will eventually be re-written to be more general.

        Returns
        -------
        view : QWebView object
        """
        # Create and fill a QWebView
        view = MapWidget(self.data_sources[self.model], self.run, width=800, height=500)
#       view.set_stations("RaobSites.csv")
        view.clicked.connect(self.map_link)

        return view

    def dropdown_menu(self, item_list):
        """
        Create and return a dropdown menu containing items in item_list.

        Params
        ------
        item_list : a list of strings for the contents of the dropdown menu

        Returns
        -------
        dropdown : a QtGui.QComboBox object
        """
        ## create the dropdown menu
        dropdown = QComboBox()
        ## set the text as editable so that it can have centered text
        dropdown.setEditable(True)
        dropdown.lineEdit().setReadOnly(True)
        dropdown.lineEdit().setAlignment(Qt.AlignCenter)

        ## add each item in the list to the dropdown
        for item in item_list:
            dropdown.addItem(item)

        return dropdown

    def update_list(self):
        """
        Update the list with new dates.

        :param list:
        :return:
        """

        if self.select_flag:
            self.select_all()
        self.profile_list.clear()
        self.prof_idx = []
        timelist = []

        fcst_hours = self.data_sources[self.model].getForecastHours()
        if fcst_hours != [ 0 ]:
            self.profile_list.setEnabled(True)
            self.all_profs.setEnabled(True)
            self.date_label.setEnabled(True)
            for fh in fcst_hours:
                fcst_str = (self.run + date.timedelta(hours=fh)).strftime(MainWindow.date_format) + "   (F%03d)" % fh
                timelist.append(fcst_str)
        else:
            self.profile_list.setDisabled(True)
            self.all_profs.setDisabled(True)
            self.date_label.setDisabled(True)

        for item in timelist:
            self.profile_list.addItem(item)
 
        self.profile_list.update()

    def update_run_dropdown(self):
        """
        Updates the dropdown menu that contains the model run
        information.
        :return:
        """

        self.run_dropdown.clear()

        times = self.data_sources[self.model].getAvailableTimes()
        if self.model == "Observed":
            self.run = [ t for t in times if t.hour in [ 0, 12 ] ][-1]
        else:
            self.run = times[-1]

        for data_time in times:
            self.run_dropdown.addItem(data_time.strftime(MainWindow.run_format))

        self.run_dropdown.update()
        self.run_dropdown.setCurrentIndex(len(times) - 1)

    def map_link(self, point):
        """
        Change the text of the button based on the user click.
        """
        if point is None:
            self.loc = None
            self.disp_name = None
            self.button.setText('Generate Profiles')
        else:
            self.loc = point['srcid'] #url.toString().split('/')[-1]
            if point['icao'] != "":
                self.disp_name = point['icao']
            elif point['iata'] != "":
                self.disp_name = point['iata']
            else:
                self.disp_name = point['srcid'].upper()

            self.button.setText(self.disp_name + ' | Generate Profiles')

    def complete_name(self):
        """
        Handles what happens when the user clicks a point on the map
        """
        if self.loc is None:
            return
        else:
            self.prof_idx = []
            selected = self.profile_list.selectedItems()
            for item in selected:
                idx = self.profile_list.indexFromItem(item).row()
                if idx in self.prof_idx:
                    continue
                else:
                    self.prof_idx.append(idx)

            if len(self.prof_idx) > 0:
                self.prof_time = selected[0].text()
                if '   ' in self.prof_time:
                    self.prof_time = self.prof_time.split("   ")[0]
            else:
                self.prof_time = self.run.strftime(MainWindow.date_format)

            self.prof_idx.sort()
            self.skewApp()


    def get_model(self):
        """
        Get the user's model selection
        """
        self.model = self.model_dropdown.currentText()

        self.update_run_dropdown()
        self.update_list()
        self.view.setDataSource(self.data_sources[self.model], self.run)

    def get_run(self):
        """
        Get the user's run hour selection for the model
        """
        self.run = date.datetime.strptime(self.run_dropdown.currentText(), MainWindow.run_format)
        self.view.setCurrentTime(self.run)
        self.update_list()

    def get_map(self):
        """
        Get the user's map selection
        """
        self.map = self.map_dropdown.currentText()

    def select_all(self):
        items = self.profile_list.count()
        if not self.select_flag:
            for i in range(items):
                if self.profile_list.item(i).text() in self.prof_idx:
                    continue
                else:
                    self.profile_list.item(i).setSelected(True)
            self.all_profs.setText("Deselect All")
            self.select_flag = True
        else:
            for i in range(items):
                self.profile_list.item(i).setSelected(False)
            self.all_profs.setText("Select All")
            self.select_flag = False

    @Slot()
    def progress_bar(self):
        value = self.progressDialog.value()
        self.progressDialog.setValue(value + 1)
        self.progressDialog.setLabelText("Profile " + str(value + 1) + "/" + str(self.progressDialog.maximum()))

    def skewApp(self):
        """
        Create the SPC style SkewT window, complete with insets
        and magical funtimes.
        :return:
        """

        items = [ item.text() for item in self.profile_list.selectedItems() ]
        fhours = [ item.split("   ")[1].strip("()") if "   " in item else None for item in items ]

        profs = []
        failure = False

        exc = ""

        ## determine what type of data is to be loaded
        ## if the profile is an observed sounding, load
        ## from the SPC website
        if self.model == "Observed":
            try:
                prof, plot_title = self.loadObserved()
                profs.append(prof)
                d = None
            except Exception as e:
                exc = str(e)
                failure = True

        ## if the profile is an archived file, load the file from
        ## the hard disk
        elif self.model == "Archive":
            try:
                prof, plot_title = self.loadArchive()
                profs.append(prof)
                d = None
            except Exception as e:
                exc = str(e)
                failure = True

        ## if the profile is a model profile, load it from the model
        ## download thread
        else:
            self.progressDialog.setMinimum(0)
            self.progressDialog.setMaximum(len(self.prof_idx))
            self.progressDialog.setValue(0)
            self.progressDialog.setLabelText("Profile 0/" + str(len(self.prof_idx)))
            self.thread = DataThread(self, model=self.model, loc=self.loc, run="%02dZ" % self.run.hour, idx=self.prof_idx)
            self.thread.progress.connect(self.progress_bar)
            self.thread.start()
            self.progressDialog.open()
            while not self.thread.isFinished():
                QCoreApplication.processEvents()
            ## return the data from the thread
            plot_title = ""
            try:
                profs, d = self.thread.returnData()
            except ValueError:
                exc = self.thread.returnData()
                self.progressDialog.close()
                failure = True

        if failure:
            msgbox = QMessageBox()
            msgbox.setText("An error has occurred while retrieving the data.")
            msgbox.setInformativeText("This probably means the data are missing for some reason. Try another site or model or try again later.")
            msgbox.setDetailedText(exc)
            msgbox.setIcon(QMessageBox.Critical)
            msgbox.exec_()
        else:
            self.skew = SkewApp(profs, d, plot_title, model=self.model, location=self.disp_name,
                prof_time=self.prof_time, run="%02dZ" % self.run.hour, idx=self.prof_idx, fhour=fhours)
            self.skew.show()

    def loadObserved(self):
        """
        Get the observed sounding based on the user's selections
        """
        ## if the profile is the latest, pull the latest profile
        if self.prof_time == "Latest":
            timestr = self.prof_time.upper()
        ## otherwise, convert the menu string to the URL format
        else:
            timestr = self.prof_time[2:4] + self.prof_time[5:7] + self.prof_time[8:10] + self.prof_time[11:-1]
            timestr += "_OBS"
        ## construct the URL
        url = urllib.urlopen('http://www.spc.noaa.gov/exper/soundings/' + timestr + '/' + self.loc.upper() + '.txt')
        ## read in the file
        data = np.array(url.read().split('\n'))
        ## necessary index points
        title_idx = np.where( data == '%TITLE%')[0][0]
        start_idx = np.where( data == '%RAW%' )[0] + 1
        finish_idx = np.where( data == '%END%')[0]

        ## create the plot title
        plot_title = data[title_idx + 1] + ' (Observed)'

        ## put it all together for StringIO
        full_data = '\n'.join(data[start_idx : finish_idx][:])
        sound_data = StringIO( full_data )

        ## read the data into arrays
        p, h, T, Td, wdir, wspd = np.genfromtxt( sound_data, delimiter=',', comments="%", unpack=True )

        ## construct the Profile object
        prof = profile.create_profile( profile='convective', pres=p, hght=h, tmpc=T, dwpc=Td,
                                wdir=wdir, wspd=wspd, location=self.loc)
        return prof, plot_title

    def loadArchive(self):
        """
        Get the archive sounding based on the user's selections.
        """
        ## construct the URL
        arch_file = open(self.link, 'r')

        ## read in the file
        data = np.array(arch_file.read().split('\n'))
        ## take care of possible whitespace issues
        for i in range(len(data)):
            data[i] = data[i].strip()
        arch_file.close()

        ## necessary index points
        title_idx = np.where( data == '%TITLE%')[0][0]
        start_idx = np.where( data == '%RAW%' )[0] + 1
        finish_idx = np.where( data == '%END%')[0]

        ## create the plot title
        plot_title = data[title_idx + 1].upper() + ' (User Selected)'

        ## put it all together for StringIO
        full_data = '\n'.join(data[start_idx : finish_idx][:])
        sound_data = StringIO( full_data )

        ## read the data into arrays
        p, h, T, Td, wdir, wspd = np.genfromtxt( sound_data, delimiter=',', comments="%", unpack=True )

        ## construct the Profile object
        prof = profile.create_profile( profile='convective', pres=p, hght=h, tmpc=T, dwpc=Td,
                                wdir=wdir, wspd=wspd, location=self.loc)
        return prof, plot_title

if __name__ == '__main__':
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

import sys
import numpy as np
from PySide import QtGui, QtCore
from sharppy.viz import plotSkewT, plotHodo, plotText, plotAnalogues
from sharppy.viz import plotThetae, plotWinds, plotSpeed, plotKinematics
from sharppy.viz import plotSlinky, plotWatch, plotAdvection, plotSTP
#from sharppy.sounding import prof, plot_title
from sharppy.io.buf_decoder import BufkitFile
#from sharppy.sharptab.profile import Profile
import sharppy.sharptab.profile as profile
from datetime import datetime

#i = 34
station = 'KSLN'
model = 'GFS'
time = '00'

station = sys.argv[3]
time = sys.argv[1]
model = sys.argv[2]

if model == "GFS":
    d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/' + model + '/' + time + '/' + model.lower() + '3_' + station.lower() + '.buf')
else:    
    d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/' + model + '/' + time + '/' + model.lower() + '_' + station.lower() + '.buf')
#d = BufkitFile('ftp://ftp.meteo.psu.edu/pub/bufkit/namm_p%236.buf')

app = QtGui.QApplication(sys.argv)
for i in range(len(d.wdir)):
    print "MAKING PROFILE OBJECT: " + datetime.strftime(d.dates[i], '%Y%m%d/%H%M')
    prof = profile.create_profile(profile='convective', location='KTOP', hght = d.hght[i], tmpc = d.tmpc[i], dwpc = d.dwpc[i], pres = d.pres[i], wspd=d.wspd[i], wdir=d.wdir[i])
    plot_title = station + ' ' + datetime.strftime(d.dates[i], '%Y%m%d/%H%M') + "  (" + time + "Z  " + model + ")"
    name = datetime.strftime(d.dates[i], '%Y%m%d.%H%M.') + time + model + '.' + station
    # Setup Application
    print "PLOTTING DATA TO FILENAME: " + name + '.png'
    #app = QtGui.QApplication(sys.argv)
    mainWindow = QtGui.QMainWindow()
    mainWindow.setGeometry(0, 0, 1180, 800)
    title = 'SHARPpy: Sounding and Hodograph Analysis and Research Program '
    title += 'in Python'
    mainWindow.setWindowTitle(title)
    mainWindow.setStyleSheet("QMainWindow {background-color: rgb(0, 0, 0);}")
    centralWidget = QtGui.QFrame()
    mainWindow.setCentralWidget(centralWidget)
    grid = QtGui.QGridLayout()
    grid.setHorizontalSpacing(0)
    grid.setVerticalSpacing(2)
    centralWidget.setLayout(grid)


    # Handle the Upper Left
    ## plot the main sounding
        #print prof.right_scp, prof.left_scp
    brand = 'Oklahoma Weather Lab'
    sound = plotSkewT(prof, pcl=prof.mupcl, title=plot_title, brand=brand)
    sound.setContentsMargins(0, 0, 0, 0)
    grid.addWidget(sound, 0, 0, 3, 1)

    # Handle the Upper Right
    urparent = QtGui.QFrame()
    urparent_grid = QtGui.QGridLayout()
    urparent_grid.setContentsMargins(0, 0, 0, 0)
    urparent.setLayout(urparent_grid)
    ur = QtGui.QFrame()
    ur.setStyleSheet("QFrame {"
                     "  background-color: rgb(0, 0, 0);"
                     "  border-width: 0px;"
                     "  border-style: solid;"
                     "  border-color: rgb(255, 255, 255);"
                     "  margin: 0px;}")
    brand = QtGui.QLabel('HOOT - Oklahoma Weather Lab')
    brand.setAlignment(QtCore.Qt.AlignRight)
    brand.setStyleSheet("QFrame {"
                        "  background-color: rgb(0, 0, 0);"
                        "  text-align: right;"
                        "  font-size: 11px;"
                        "  color: #FFFFFF;}")
    grid2 = QtGui.QGridLayout()
    grid2.setHorizontalSpacing(0)
    grid2.setVerticalSpacing(0)
    grid2.setContentsMargins(0, 0, 0, 0)
    ur.setLayout(grid2)

    speed_vs_height = plotSpeed( prof )
    speed_vs_height.setObjectName("svh")
    inferred_temp_advection = plotAdvection(prof)
    hodo = plotHodo(prof.hght, prof.u, prof.v, prof=prof, centered=prof.mean_lcl_el)
    storm_slinky = plotSlinky(prof)
    thetae_vs_pressure = plotThetae(prof)
    srwinds_vs_height = plotWinds(prof)
    watch_type = plotWatch(prof)

    grid2.addWidget(speed_vs_height, 0, 0, 11, 3)
    grid2.addWidget(inferred_temp_advection, 0, 3, 11, 2)
    grid2.addWidget(hodo, 0, 5, 8, 24)
    grid2.addWidget(storm_slinky, 8, 5, 3, 6)
    grid2.addWidget(thetae_vs_pressure, 8, 11, 3, 6)
    grid2.addWidget(srwinds_vs_height, 8, 17, 3, 6)
    grid2.addWidget(watch_type, 8, 23, 3, 6)
    urparent_grid.addWidget(brand, 0, 0, 1, 0)
    urparent_grid.addWidget(ur, 1, 0, 50, 0)
    grid.addWidget(urparent, 0, 1, 3, 1)

    # Handle the Text Areas
    text = QtGui.QFrame()
    text.setStyleSheet("QWidget {"
                       "  background-color: rgb(0, 0, 0);"
                       "  border-width: 2px;"
                       "  border-style: solid;"
                       "  border-color: #3399CC;}")
    grid3 = QtGui.QGridLayout()
    grid3.setHorizontalSpacing(0)
    grid3.setContentsMargins(0, 0, 0, 0)
    text.setLayout(grid3)
    convective = plotText(prof)
    #convective = QtGui.QFrame()
    #kinematic = QtGui.QFrame()
    kinematic = plotKinematics(prof)
    SARS = plotAnalogues(prof)
    stp = plotSTP(prof)
    grid3.addWidget(convective, 0, 0)
    grid3.addWidget(kinematic, 0, 1)
    grid3.addWidget(SARS, 0, 2)
    grid3.addWidget(stp, 0, 3)
    grid.addWidget(text, 3, 0, 1, 2)
    pixmap = QtGui.QPixmap.grabWidget(mainWindow)
    pixmap.save(name + '.png', 'PNG', 100)
    #    mainWindow.show()
    print "DONE PLOTTING."
    #app.exec_()

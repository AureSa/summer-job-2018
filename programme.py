from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

import sys
from socket import *
import time
import csv

import classGui

#pyuic5 GUI.ui -o classGui.py

class MainGUI(QMainWindow, classGui.Ui_MainWindow):
    """Création de la classe principale qui vas gérer l'interface graphique"""

    def __init__(self, parent=None):
        """Constructeur de la classe"""

        ###Initialisation de l'interface graphique###
        super().__init__(parent)           #initialisation des classes mères
        self.setupUi(self)                 #création de l'interface graphique a partire du fichier contenant les widgets

        ###Récupération des données du fichiers###
        with open("donnees.txt", 'r') as file:
            data =file.readlines()
            ip =data[0].split(':')[1].strip()
            ctemp =data[1].split(':')[1].strip()
            cdebit =data[2].split(':')[1].strip()


        ###Création des variables utiles au déroulement du programme###
        self.adrIP =ip                      #adresse IP de l'arduino
        self.Port =5000
        self.temps =[]                      #liste temporelle
        self.meas =[ [], [], [], []]        #liste de 4 sous listes pour récupérer les mesures des sondes
        self.timeStep =1000                 #intervalle de temps entre chaque mesure initialiser a 1000ms
        self.affichage =[]                  #liste d'affichage des courbes sur le graphique
        self.debit =0                       #variable du débit en L/s
        self.passage =0                     #variable qui correspond au nombre de passage dans la fonction de récupération de donnée
        self.measPoint =1                   #variable qui correspond au nombre de points de mesure

        ###Coefficient pour les mesure###
        self.coefTemp =eval(ctemp)          #plage de température des sonde -20->100 plage du can 0->1023
        self.coefDebit =eval(cdebit)        #sortie du capteur 3300 pulsation/L donc 1 pulse=1/3300


        ###Création des buffer d'état###
        self.maBuffer =False        #buffer de marche =True, arrêt =False
        self.infBuffer =False       #buffer mesure infine =True, limité =False


        ###Création du graphique###
        self.figure = plt.figure(1)                             #création d'une figure de ploting
        self.canvas = FigureCanvas(self.figure)                 #création d'un canvas de dessin
        self.toolbar = NavigationToolbar(self.canvas, self)     #création d'une barre des tâches matplotlib

        self.graphLay.addWidget(self.toolbar)                   #on ajoute la barre des tâches dans le layout du graphique
        self.graphLay.addWidget(self.canvas)                    #on ajoute le canvas dans le layout du graphique
        self.setLayout(self.graphLay)                           #affichage du graphique sur l'interface

        ax = self.figure.add_subplot(111)                       #on ajoute un traceur initial sur la figure de ploting

        ###Création des timer###
        self.sondeTimer =QTimer()                           #création d'un timer pour la récupération des températures
        self.sondeTimer.timeout.connect(self.recupData)     #connexion du timer a la fonction de récupération des températures

        self.debitTimer =QTimer()                           #création d'un timer pour la récupération du débit
        self.debitTimer.timeout.connect(self.majDebit)      #connexion du timer a la fonction de récupération du débit

        ###Initialisation des variables Ethernet###

        self.address = ( self.adrIP, self.Port)             #création d'un tuple contenant les paramètres de la connexion: @IP client + PORT
        self.socketClient = socket(AF_INET, SOCK_DGRAM)     #création d'un socket de communication
        self.socketClient.settimeout(1)                     #définition du timeout de le connexion ethernet

        ###Vérification de la communication ethernet###
        try:
            for i in range(0, 3):         #3 essaie
                self.socketClient.sendto(b"OK?", self.address)      #envoie de la trame de vérification de présence
                rec_data, addr = self.socketClient.recvfrom(2048)   #lectures des données envoyer par l'arduino
                if rec_data.decode("utf_8") == "OK":                #vérification de la trame retourner
                   #trame ok
                   self.LBcoEth.setText("Connexion Ethernet ON")    #mise à jour du texte informatif
                   self.BTma.clicked.connect(self.startStop)        #on connect le bouton marche/arrêt a la fonction de démarrage
                   self.LBadrEth.setText(self.adrIP)                #on affiche l'adresse IP de la carte arduino
                   self.debitTimer.start(1000)                      #on démarre le timer de récupération de débit
                   break                                            #on quitte la boucle

        except:                         #si on a une erreur
            self.ethernetProb()         #on passe dans la fonction de gestion des problèmes ethernet

        ###Connexion des différents widgets a leur fonction###

        #connexion des checkbox des valeur a afficher sur le graphique
        self.CKsonde1.stateChanged.connect(self.sondePlot)
        self.CKsonde2.stateChanged.connect(self.sondePlot)
        self.CKsonde3.stateChanged.connect(self.sondePlot)
        self.CKsonde4.stateChanged.connect(self.sondePlot)

        self.CKinf.stateChanged.connect(self.infinity)      #connexion de la checkbox qui permet de faire une mesure inifinie

        self.SPmeasPts.valueChanged.connect(self.point)     #connexion de la spinbox qui permet de saisir le nombre de point mesure

        self.BTsave.clicked.connect(self.saveData)          #connexion du bouton de sauvegarde a la fonction d'écriture

        self.BTreset.clicked.connect(self.reset)

        ### FIN DU CONSTRUCTEUR ###



    def ethernetProb(self):
        """Méthode appeller lorsqu'un problème ethernet est détecter"""

        self.LBcoEth.setText("Connexion Ethernet OFF")          #mise a jour du texte informatif
        self.LBadrEth.setText("None")                           #on modifie l'adresse IP

        self.debitTimer.stop()                                  #arrêt du timer de récupération de débit
        self.sondeTimer.stop()                                  #arrêt du timer de mesure

        self.BTma.setText("Retry")                              #on change le nom du bouton marche arrêt
        try:
            self.BTma.clicked.disconnect(self.startStop)
        except:
            pass
        self.BTma.clicked.connect(self.ethRetry)                #on connecte le bouton retry a la fonction de démarrage de communication ethernet

        self.LBmeasState.setStyleSheet(                         #on met le bg de l'indicateur de mesure en rouge
            "QLabel {background: red;}")
        self.LBmeasState.setText("  Mesures OFF")               #on met à jour le texte informatif
        self.maBuffer =False

        ### FIN DE LA METHODE -ETHERNETPROB- ###



    def ethRetry(self):
        """Méthode qui permet de re-tester la communication ethernet avec l'arduino"""


        for i in range(0, 3):                                       #on tente la connexion 3 fois
            try:
                self.socketClient.sendto(b"OK?", self.address)      #on envoie la requête de présence
                rec_data, addr = self.socketClient.recvfrom(2048)   #on tente de récupérer la réponse

                if rec_data.decode("utf_8") == "OK":                #si la réponse est bonne
                    self.LBcoEth.setText("Connexion Ethernet ON")   #on modifie le texte d'état de la connexion ethernet
                    self.BTma.setText("Marche/Arrêt")               #on modofie les paramètres du boutons

                    self.BTma.clicked.connect(self.startStop)       #on connecte le bouton a la fonction de marche/arrêt

                    self.LBadrEth.setText(self.adrIP)               #on affiche l'adresse IP de la carte
                    self.debitTimer.start(1000)                     #on démarre le timer de récupération de débit
                    self.BTma.clicked.disconnect(self.ethRetry)
                    break                                           #on sort de la boucle
            except:
                continue

        ### FIN DE LA METHODE -ETHRETRY- ###



    def startStop(self):
        """Méthode de démarrage/arrêt de la récupération des données"""
        self.maBuffer ^= True                       #complémentation de l'état marche/arrêt

        self.timeStep =self.SPtimeStep.value()*1000 #on récupère l'intervalle de temps

        self.passage =0                                 #on initialise le nombre de passage a 0

        if self.maBuffer == True:                       #si on démarre les mesures
            self.sondeTimer.start(self.timeStep)        #on démarre le timer de récupération des données avec l'intervalle de temps choisis
            self.LBmeasState.setStyleSheet(             #on met le bg de l'indicateur de mesure en vert
            "QLabel {background: green;}")
            self.LBmeasState.setText("  Mesures ON")    #on met a jour le texte informatif

            self.BTsave.setEnabled(False)

        else:                                           #si on arrête
            self.sondeTimer.stop()                      #on arrête le timer de mesures
            self.LBmeasState.setStyleSheet(             #on met le bg de l'indicateur de mesure en rouge
            "QLabel {background: red;}")
            self.LBmeasState.setText("  Mesures OFF")   #on met à jour le texte informatif

            self.BTsave.setEnabled(True)

        ### FIN DE LA METHODE -STARTSTOP- ###



    def recupData(self):
        """Méthode de récupération des données sur l'arduino"""

        ###mise à jour des paramètres temporels###
        self.passage +=1                                            #on incrémente le nombre de passge dans la fonction
        try:
            self.temps.append(self.temps[-1]+self.timeStep/1000)    #on ajoute la temps correspondants dans la liste temporelle
        except:
            self.temps.append(self.timeStep/1000)

        ###récupération des données###

        self.socketClient.sendto(b"temp", self.address)             #on envoie la requête pour récupérer les données de tempréture

        try:         #on tente de récupérer les données

            rec_data, addr = self.socketClient.recvfrom(2048)   #lectures des données envoer par l'arduino
            rec_data =eval(rec_data)                            #on convertie les données en tuples

            for i in range(0, 4):                               #on met les données dans les listes de stockages
                self.meas[i].append(rec_data[i]*self.coefTemp)

        except:     #sinon on fais rien et on continue la boucle
            for i in range(0, 4):
                if len(self.meas[i]) != len(self.temps):
                    self.meas[i].append(self.meas[i][-1])
            self.ethernetProb()

        ###mise à jour du graphique###
        self.majPlot()

        ### FIN DE LA METHODE -RECUPDATA-



    def majPlot(self):
        """Méthode de mise à jour du graphique appelé a chaque récupération de données"""

        ###affichage des données###
        self.figure.clear()                         #on efface la figure précédente

        ax = self.figure.add_subplot(111)           #on recréer des axe de ploting

        for i in self.affichage:                    #on affiche les données des sondes
            ax.plot(self.temps, self.meas[i])

        ###configuration des limites des axes###

        if self.temps[-1]<20:                                      #si on a moins de 20 points de mesures on affiche de 0 à 20
            ax.set_xlim([0, 20])

        else:
            ax.set_xlim([self.temps[-1]-18, self.temps[-1]+2])   #sinon on affiche 18 valeurs derrière et 2 unité vide devant

        ###réaffichage du graphique###
        self.canvas.draw()

        ###vérification du nombre de passage###
        if self.passage >= self.measPoint and self.infBuffer == False:  #si on a dépasser le nombre de points max et si on est pas en mode infinie
            self.startStop()                                            #on passe dans la fonction de stop

        ### FIN DE LA METHODE -MAJPLOT- ###



    def majDebit(self):
        """Méthode de récupération et de mise à jour du débit"""

        self.socketClient.sendto(b"debit", self.address)             #on envoie la requête pour récupérer les données de tempréture


        try:         #on tente de récupérer les données

            rec_data, addr = self.socketClient.recvfrom(2048)       #lectures des données envoer par l'arduino
            rec_data =eval(rec_data)*self.coefDebit                 #on convertie les données en tuple
            self.LBdebit.setText("Débit {0} L/s".format(rec_data))  #on met à jour l'affichage



        except:     #sinon on fais rien et on continue la boucle
            self.ethernetProb()

        ### FIN DE LA METHODE -MAJDEBIT- ###



    def saveData(self):
        """Méthode qui permet de sauvegarder les données dans un fichiers csv"""
        data =[["temps", "sonde n°1", "sonde n°2", "sonde n°3", "sonde n°4"]]

        ###ouverture de la boite de dialogue de sélection du fichier###
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","Cvs File (*.csv);;All Files (*)", options=options)

        ###formatage des données avant sauvegarde: [temps, sonde1, sonde2, sonde3, sonde4]
        if fileName:

            for i in range(0, len(self.temps)):     #on parcours toutes les données récupérer
                liste =[self.temps[i]]              #on ajoute le temps dans la première colonnes
                for sonde in self.meas:             #on parcours toutes les mesures de sondes
                    liste.append(sonde[i])          #on met une mesure de sonde ar colonne

                data.append(liste)                  #on ajoutes les données a la liste de sauvegarde

            ###écriture dans le fichier de sauvegarde###
            with open(fileName, 'w', newline='') as f:  #on ouvre le fichier
                writer = csv.writer(f)                  #on crée un writer qui permettra d'écrire dans le fichier
                writer.writerows(data)                  #on écrit ensuite les données dans le fichier

                ###remise a zéros des mesures###
                self.temps =[]
                self.meas =[ [], [], [], [] ]

        ### FIN DE LA METHODE -SAVEDATA- ###



    def reset(self):
        """Méthode qui permet de remettre a zéros les données enregistrer"""

        ###reste des données###
        self.temps =[]
        self.meas =[ [], [], [], [] ]

        ###reset du graphique###
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.canvas.draw()

        ### FIN DE LA METHODE -RESET- ###



    def sondePlot(self, state):
        """Méthode qui permet de mettre à jour les sondes à afficher sur le graphique"""

        sender =self.sender().text()                                #on récupère le nom du widget qui a envoyer le signal

        name =["Sonde n°1", "Sonde n°2", "Sonde n°3", "Sonde n°4"]  #on crée une liste des noms de widget envoyeur

        for i in range(0, 4):                                       #on parcours la liste des envoyeurs
            if sender == name[i]:                                   #on détecte l'envoyeur
                if state == Qt.Checked:                             #si la case est cochée
                    self.affichage.append(i)                        #on ajoute l'indice de l'envoyeur a la liste des sondes à afficher
                else:                                               #si la case est décocher
                    self.affichage.remove(i)                        #on retire l'indice de l'envoyeur a la liste des sondes à aficher
                break                                               #on arrête la boucle
            else:                                                   #si l'envoyeur n'est pas le bon
                continue                                            #on continue la boucle pour trouver le bon

        self.affichage.sort()                                       #on range ensuite la liste d'affiche dans l'ordre croissant

        ### FIN DE LA METHODE -SONDEPLOT- ###



    def infinity (self, state):
        """Méthode qui permet de passer en mode mesure infinie"""

        if state == Qt.Checked:     #si la case est cochée
            self.infBuffer =True    #on passe le buffer d'infinité a True
        else:                       #si la case est décochée
            self.infBuffer =False   #on passe le buffer d'infinité a False

        ### FIN DE LA METHODE -INFINITY- ###



    def point(self):
        """Méthode qui met à jour le nombre de point maximal a mesurer"""

        self.measPoint =self.SPmeasPts.value()   #récupération du nombre de point de mesure

        ### FIN DE LA METHODE -POINT- ###


    ### ~~~ FIN DE LA CLASSE MAINGUI ~~~ ###




if __name__=='__main__':
    app = QApplication(sys.argv)
    Interface =MainGUI()
    Interface.show()
    app.exec_()
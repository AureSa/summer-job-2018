///Inclusion des librairie///
#include <Ethernet.h>   //Librairie ethernet
#include <EthernetUdp.h>  //Librairie UDP
#include <SPI.h>          //Librairie spi pour la communication entre la carte et le shield

///Initialisation des variables///
IPAddress ip(169, 254, 68, 134);  // /!\ l'adresse IP doit être dans le même sous réseau que l'ordinateur
byte mac[] ={0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xEE}; //adresse mac de l'arduino
char packetBuffer[UDP_TX_PACKET_MAX_SIZE];        
String datReq;      //Données a récupérer
int packetSize;     //taille du packet récupérer
EthernetUDP Udp;    //objet Udp
unsigned int localPort = 5000;
int duty =160;

int sonde1 =0, sonde2 =0, sonde3 =0, sonde4 =0; //variable CAN des sondes
volatile int debit =0;     //variable pour le débit
String envoie ="a,b,c,d";   //format de la chaine d'envoie

void setup() {
  // put your setup code here, to run once:
  Ethernet.begin(mac, ip);   //ouverture de la communication ethernet
  Udp.begin(localPort);     //initialisation de l'udp
  delay(1500);    //petite attente avant de passer au loop
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(0, debFct, RISING);


  TCCR1A = 0;           // undo the configuration done by...
  TCCR1B = 0;           // ...the Arduino core library
  TCNT1  = 0;           // reset timer
  TCCR1A = _BV(COM1A1)  // non-inverted PWM on ch. A
         | _BV(COM1B1)  // same on ch; B
         | _BV(WGM11);  // mode 10: ph. correct PWM, TOP = ICR1
  TCCR1B = _BV(WGM13)   // ditto
         | _BV(CS10);   // prescaler = 1
  ICR1   = 320;         // TOP = 320

    // Set the PWM pins as output.
    pinMode( 9, OUTPUT);

    analogWrite25k(9, duty);
}

void loop() {
  // put your main code here, to run repeatedly:

  packetSize =Udp.parsePacket();  //lecture de la taille du packet udp

  if (packetSize>0) {   //vérifie si une requête est présente
      Udp.read(packetBuffer, UDP_TX_PACKET_MAX_SIZE);   //lecture des données
      String datReq(packetBuffer);  //convertion de la requête en string
      

      if (datReq == "OK?")  //requête de vérification de présence
      {
        Udp.beginPacket(Udp.remoteIP(), Udp.remotePort());  //ouverture de la communication udp
        Udp.print("OK"); //envoie de la réponse
        Udp.endPacket(); //fermeture de la communication udp
      }

      else if (datReq == "temp")
      {
        //lecture des sondes de température
        sonde1 =analogRead(A0);
        sonde2 =analogRead(A1);
        sonde3 =analogRead(A2);
        sonde4 =analogRead(A3);

        //formatage de la chaine d'envoie
        envoie.replace("a", String(sonde1));
        envoie.replace("b", String(sonde2));
        envoie.replace("c", String(sonde3));
        envoie.replace("d", String(sonde4));

        //envoie de la chaine
        Udp.beginPacket(Udp.remoteIP(), Udp.remotePort()); //ouverture de la communication udp
        Udp.print(envoie);
        Udp.endPacket();
        
        envoie ="a,b,c,d";  //reset de la trame d'envoie
        
      }

      else if (datReq ="debit")
      {
        Udp.beginPacket(Udp.remoteIP(), Udp.remotePort());
        Udp.print(String(debit));
        Udp.endPacket();
        debit =0;
      }

      else
      {
        duty =datReq.toInt();
        if ( (duty>=0) && (duty<=320) )
        {
          analogWrite25k(9, duty);
        }
      }

      
  }

  memset(packetBuffer, 0, UDP_TX_PACKET_MAX_SIZE);

}

void debFct()
{
  debit++;
}

void analogWrite25k(int pin, int value)
{
    switch (pin) {
        case 9:
            OCR1A = value;
            break;
        case 10:
            OCR1B = value;
            break;
        default:
            // no other pin will work
            break;
    }
}

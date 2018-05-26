import cherrypy
import json
import hashlib
import mimetypes
import os
import urllib2
import sqlite3
import time


#This API allows other clients to send this client a message
@cherrypy.expose
def receiveMessage(data):


    try:

        sender = data['sender']
        destination =  data['destination']
        message = data['message']
        stamp = str(time.time())
        #stamp = data['stamp']

        #Prepare database for storing message    
        workingDir = os.path.dirname(__file__)
        dbFilename = workingDir + "/db/messages.db"
        f = open(dbFilename,"r+")
        conn = sqlite3.connect(dbFilename)
        cursor = conn.cursor()

        
        cursor.execute("INSERT INTO Received(UPI,Messages,Stamp) VALUES (?,?,?)",[sender,message,stamp])

        conn.commit()
        conn.close()

        return '0'
        
    except KeyError:

        return '1';




#Calls the destination's /receiveMessage API to send a message to them
@cherrypy.expose
def sendMessage(message):


    #Check session
    try:
        username = cherrypy.session['username']
        destination = cherrypy.session['chatTo']

        if (message == None or len(message) == 0):
            raise cherrypy.HTTPRedirect('/chat?userUPI='+destination)
        else :
            #Open database
            workingDir = os.path.dirname(__file__)
            dbFilename = workingDir + "/db/userlist.db"
            f = open(dbFilename,"r+")
            conn = sqlite3.connect(dbFilename)
            cursor = conn.cursor()

            #Find ip and port - Should always exist, since this method is only called when this user is saved.
            cursor.execute("SELECT IP,PORT FROM UserList WHERE UPI = ?",[destination])
            row = cursor.fetchall()
            ip = str(row[0][0])
            port = str(row[0][1])

            #Ping destination to see if they are online
            pingResponse = urllib2.urlopen("http://"+ip+":"+port+"/ping?sender="+str(username)).read()

            #If destination was pinged successfully
            if (pingResponse == '0'):

                stamp = str(time.time())
                url = "http://"+ip+":"+port+"/receiveMessage"

                output_dict = {'sender' :username,'message':message,'stamp':stamp,'destination':destination}  	
                data = json.dumps(output_dict) 	
                req = urllib2.Request(url,data,{'Content-Type':'application/json'})

                response = urllib2.urlopen(req).read()
    	    
                if (response[0] == '0'):
                    #Keep them on chat page
                    saveMessage(message,destination)
                    raise cherrypy.HTTPRedirect('/chat?userUPI='+destination)
                else:
                    print 'Code error : ' + response[0]
                    return 'Message not sent but ping response is 0'

    except KeyError:

        return 'Session expired'


@cherrypy.expose
def getChatPage(userUPI):

    #Check session
    try:
        username = cherrypy.session['username']
        #Serve chat page html
        workingDir = os.path.dirname(__file__)
        filename = workingDir + "/html/chatbox.html"
        f = open(filename,"r")
        page = f.read()
        f.close()
        cherrypy.session['chatTo'] = userUPI

        dbFilename = workingDir + "/db/messages.db"
        f = open(dbFilename,"r")
        conn = sqlite3.connect(dbFilename)
        cursor = conn.cursor()

        cursor.execute("SELECT Messages FROM Received WHERE UPI = ?",[userUPI])

        rows = cursor.fetchall()

        for row in rows:
            page += '<div class = "chat friend">'
            page += '<div class = "user-photo" src = "/static/html/anon.png"></div>'
            page += '<p class = "chat-message">' + str(row[0]) + '</p>'
            page += '</div>'

        cursor.execute("SELECT Messages FROM Sent WHERE UPI = ?",[userUPI])

        rows = cursor.fetchall()

        for row in rows:
            page += '<div class = "chat self">'
            page += '<div class = "user-photo" src = "/static/html/anon.png"></div>'
            page += '<p class = "chat-message">' + str(row[0]) + '</p>'
            page += '</div>'

        filename = workingDir + "/html/chatbox-bottom.html"
        f = open(filename,"r")
        page += f.read()
        f.close()


        return page

    except KeyError:

        return 'Session expired'


#Public Ping API for checking if this client is online
@cherrypy.expose
def ping(sender):

    return '0'

@cherrypy.expose
def saveMessage(message,destination):

    #Open database
    workingDir = os.path.dirname(__file__)
    dbFilename = workingDir + "/db/messages.db"
    f = open(dbFilename,"r+")
    conn = sqlite3.connect(dbFilename)
    cursor = conn.cursor()

    stamp = str(time.time())

    cursor.execute("INSERT INTO Sent(UPI,Messages,Stamp) VALUES (?,?,?)",[destination,message,stamp])

    conn.commit()
    conn.close()

@cherrypy.expose
def getPublicKey():
    pass

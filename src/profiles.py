import cherrypy
import json
import mimetypes
import os
import urllib
import urllib2
import sqlite3

port = 15010


#Call other node's getProfile
@cherrypy.expose
def viewProfile(destination):

    #Check session
    try:

        username = cherrypy.session['username']
        profile_username = destination

        #Open database
        workingDir = os.path.dirname(__file__)
        dbFilename = workingDir + "/db/userinfo.db"
        f = open(dbFilename,"r+")
        conn = sqlite3.connect(dbFilename)
        cursor = conn.cursor()

        #Find ip and port - Should always exist, since this method is only called when this user is saved.
        cursor.execute("SELECT IP,PORT FROM UserList WHERE UPI = ?",[profile_username])
        row = cursor.fetchall()
        ip = str(row[0][0])
        port = str(row[0][1])

        #Construct URL for requesting profile
        url = "http://"+ip+":"+port+"/getProfile"

        #Encode input arguments into json
        output_dict = {'sender' :username,'profile_username':profile_username}
        data = json.dumps(output_dict)

        #Put arguments into url header  
        req = urllib2.Request(url,data,{'Content-Type':'application/json'})

        #Attempt to retrieve profile.
        try:

            #Load json encoded profile. Give 4 second for other side to respond.
            data = urllib2.urlopen(req,timeout= 4).read()
            loaded = json.loads(data)

            #Get relevant information from the profile.
            name = loaded.get('fullname','')
            position = loaded.get('position','')
            description = loaded.get('description','')
            location = loaded.get('location','')
            picture = loaded.get('picture','')

            #Open database and store the user profile information
            workingDir = os.path.dirname(__file__)
            dbFilename = workingDir + "/db/userinfo.db"
            f = open(dbFilename,"r+")
            conn = sqlite3.connect(dbFilename)
            cursor = conn.cursor()

            #Check if user profile exists in this database file
            cursor.execute("SELECT Name FROM Profile WHERE UPI = ?",[profile_username])
            row = cursor.fetchall()

            #Insert new user information if new, otherwise update existing profile.
            #TODO: ADD lastUpdated implementation
            if (len(row) == 0):
                cursor.execute("INSERT INTO Profile(Name,Position,Description,Location,Picture) VALUES (?,?,?,?)",[name,position,description,location,picture])
            else:
                cursor.execute("UPDATE Profile SET Name = ?,Position = ?,Description = ?,Location = ?,Picture = ? WHERE UPI = ?",[name,position,description,location,picture,profile_username])


            #Attempt to save the profile image from the given url.
            try:
                urllib.urlretrieve(picture, workingDir + "/serve/serverFiles/profile_pictures/"+profile_username+".jpg")
                cursor.execute("UPDATE Profile SET Picture = ? WHERE UPI = ?",["/serve/serverFiles/profile_pictures/"+profile_username+".jpg",profile_username])
            except urllib2.URLError, exception:
                pass

            #Save database changes
            conn.commit()
            conn.close()
            
            return data

        #In case API call fails.
        except urllib2.URLError, exception:

            return 'Sorry, we couldn\'t fetch this profile. Please try again later.'


    except KeyError:

        return 'Session Expired'



#Allows other users to request a profile from this node
@cherrypy.expose
def getProfile(data):

    #Try block; in case the API caller didn't add the compulsory input arguments
    try:

        #Extract inputs for this API call
        profile_username = data['profile_username']
        sender = data['sender']

        #Get user's ip address
        hostIP = urllib2.urlopen('https://api.ipify.org').read()
        """For internal ip address"""
        #hostIP =socket.gethostbyname(socket.gethostname())


        #Construct URL for image
        url = "http://" + hostIP + ":" + str(port) + "/static/serverFiles/profile_pictures/" + profile_username + ".png"


        #Open database for extracting profile
        workingDir = os.path.dirname(__file__) 
        dbFilename = workingDir + "/db/userinfo.db"
        f = open(dbFilename,"r")
        conn = sqlite3.connect(dbFilename)
        cursor = conn.cursor()


        #Read database and see if requested profile exists
        cursor.execute("SELECT Name,Position,Description,Location,Picture,lastUpdated FROM Profile WHERE UPI = ?",[profile_username])
        row = cursor.fetchone()

        conn.close()

        #Check if profile exists in the database
        if (len(row) != 0):

            #Extract profile information in the rows and store it into a dictonary object to json encode later
            output_dict = {'fullname' :row[0],'position': row[1],'description': row[2],'location': row[3],'picture': url,'lastUpdated':row[5]}

            #Json encode the output dictionary then return it
            data = json.dumps(output_dict)
            return data

        else:

            return 'Requested profile does not exist'


    #Return error code 1 : Missing compulsory field
    except KeyError:

        return '1'



#Function that saves user's profile edits
@cherrypy.expose
def saveEdit(name,position,description,location,picture):
    
    #Check user session
    try:

        username = cherrypy.session['username']  

        #Prepare database for writing to
        workingDir = os.path.dirname(__file__)
        dbFilename = workingDir + "/db/userinfo.db"
        f = open(dbFilename,"r+")
        conn = sqlite3.connect(dbFilename)
        cursor = conn.cursor()

        #Checks if anything was uploaded, and makes sure that it is an image(.png and .jpg only supported currently).
        #Then update the profile.
        if (picture != ''):
            if (picture.endswith('.jpg') or picture.endswith('.png')):
                picture = "/static/serverFiles/profile_pictures/" + picture
                cursor.execute("UPDATE Profile SET Name = ?,Position =?,Description = ?,Location = ? ,Picture = ? WHERE UPI = ?",[name,position,description,location,picture,username])
        else:
            cursor.execute("UPDATE Profile SET Name = ?,Position =?,Description = ?,Location = ?  WHERE UPI = ?",[name,position,description,location,username])


        #Save database changes and return to userpage
        conn.commit()
        conn.close()

        raise cherrypy.HTTPRedirect('/showUserPage')

    #Redirect to index
    except KeyError:

        raise cherrypy.HTTPRedirect('/')



    

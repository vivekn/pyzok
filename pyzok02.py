
#!/usr/bin/python
#
# pyzok chat server v0.2  (August 1st 2010)
# by
# Vivek Narayanan<mail@vivekn.co.cc>
#
# released under GNU GPL 2.0
#
#
# This is a text based chat server,to use it simply execute this .py file
# From the client side,connect using pChat or any Mud/Moo client or design your own client
#
# You can add new commands by creating a function do_xxxx in the class definition of ChatRoom,
# replace xxxx with the command
#
__author__="Vivek"
__date__ ="$14 May, 2010 8:08:22 PM$"

from socket import *
import asyncore
import socket
from asyncore import dispatcher
from asynchat import async_chat
#Message Codes
ERR = '!!Error\r\n'
MSG = '!!Msg\r\n'
SERV = '!!SM\r\n'
LIST = '!!List\r\n'
ADDR = '!!Addr\r\n'
STAT = '!!Stat\r\n'



if __name__ == "__main__":
    class EndSession(Exception): pass #This is used for handling a user logging out
    class CommandHandler:
        server=None
        def unknown(self, session, cmd,line):
            session.push(ERR + 'Unknown command: %s\r\n' % cmd)
        def handle(self, session, line):
            '''
            This function handles the data received by the server.If the incoming
            text contains a command , it checks a function do_command exists and if it does
            it calls the function.
            '''
            ori=line
            print ori
            self.server.log+='%s:%s\r\n'%(ori,line)  #appends data to server log
            if not line.strip():
                return
            parts = line.split(' ', 1)
            cmd = parts[0]
            try: line = parts[1].strip()
            except IndexError: line = ''

            meth = getattr(self, 'do_'+cmd, None)

            if callable(meth):
                meth(session, line)
            else:
                self.unknown(session, cmd,ori)
    class Room(CommandHandler):

        '''
        Class extending a CommandHandler,forms the basis for a chatroom
        '''

        def __init__(self, server,name='',msg=''''''):
            self.server = server
            self.name = name
            self.sessions = []
            self.msg=msg
        def add(self, session):
            self.sessions.append(session)
        def remove(self, session):
            self.sessions.remove(session)
        def broadcast(self, line):
            for session in self.sessions:
                session.push(MSG+line)
        def do_logout(self, session, line):
            raise EndSession
    class LoginRoom(Room):
        '''
        The user first logs in to this room when he or she connects to the server.
        '''
        def add(self, session):
            Room.add(self, session)
            self.broadcast('Welcome to %s\r\n' % (self.server.name))
            print session

        def unknown(self, session, cmd,line):
            session.push(SERV+'Please log in\nUse "login <nick>"\r\n')
        def do_login(self, session, line):
            name = line.strip()
            if not name:
                session.push(ERR+'Please enter a name\r\n')
            elif name in self.server.users:
                session.push(ERR+'The name "%s" is taken.\r\n' % name)
                session.push(ERR+'Please try again.\r\n')
            else:
                session.name = name
                session.enter(self.server.rooms[0])
                session.push(SERV+"Welcome to "+self.server.name+','+line.strip()+'\r\n')
        def do_admin(self,session,line):
            #used to authenticate an admin user
            name=line.split(' ', 1)
            if name[0]in self.server.admins:
                try:

                    if self.server.admins[name[0]]==name[1]:
                        session.isAdmin=True
                        session.name=name[0]
                        session.enter(self.server.rooms[0])
                        session.push(SERV+"Welcome to "+self.server.name+','+name[0]+'\r\nYou now have admin privileges\r\n')
                    else:
                        session.push(ERR+"Authentication Failed. \r\n")

                except Exception,e:session.push(ERR+"Error:"+str(e)+'\r\n')

            else:
                session.push(ERR+"Authentication Failed. \r\n")






    class ChatRoom(Room):

        def add(self, session):

            self.broadcast(session.name + ' has entered the room.\r\n')
            self.server.users[session.name] = session
            Room.add(self, session)

            if len(self.msg):
                self.play_welcome_message(session, self.msg)
        def remove(self, session):
            Room.remove(self, session)
            self.broadcast(session.name + ' has left the room.\r\n')
        def do_say(self, session, line):
            # 1 to all message,format:say message
            self.broadcast(session.name+': '+line+'\r\n')
        def do_pm(self,session,line):
            # 1 on 1 chat,format:say user message
            sent=0
            user = line.split(' ',1)
            for a in self.sessions:
                if a.name==user[0]:
                    a.push(MSG+'pm from '+session.name+': '+user[1]+'\r\n')
                    sent=1
                    break
            if not sent:
                session.push(ERR+'User %s not found\r\n'%user[0])

        def do_ulist(self, session, line):
            #lists all users in the room
            session.push(LIST)
            for other in self.sessions:
                session.push(other.name + '\r\n')
        def do_sulist(self, session, line):
            #lists all users connected to the server
            session.push(LIST)
            for name in self.server.users:
                session.push(name +'~~' + self.server.users[name].status + '\r\n')
        def unknown(self,session,cmd,line):
            #when no specific command is given,it is treated as a normal (1 to many) chat message,format:message

            self.broadcast(session.name+': '+line+'\r\n')
        def do_newroom(self,session,line):
            #for creating a new room,requires the user to be admin,format:newroom room_name
            if session.isAdmin==True:
                try:
                    self.server.new_room(line.strip())
                    session.push(SERV+'A new room %s has been created.\r\n'%line.strip())
                except Exception,e:
                    session.push(ERR+'Error occured:'+str(e)+'\r\n')
            else:
                session.push(ERR+'You do not have the required permissions.\r\n')

        def do_delroom(self,session,line):
            #for deleting a room,requires the user to be admin,format:delroom room_name
            if session.isAdmin==True and line.strip()!='Home':
                try:
                    self.server.del_room(line.strip())
                    session.push(SERV+'The room %s has been deleted\r\n'%line.strip())
                except Exception,e:
                    session.push(ERR+'Error occured:'+str(e)+'\r\n')
            else:
                session.push(ERR+'You do not have the required permissions.\r\n')

        def do_serverlogs(self,session,line):
            #for writing the string log,which stores the activity log to a file,format:serverlogs [filename]
            if session.isAdmin==True:
                try:
                    if len(line.strip()):
                        self.server.writelogs(line.strip())
                    else: self.server.writelogs()
                except Exception:pass
                else:server.push(SERV+"Server logs written to file successfully\r\n")
            else:
                session.push(ERR+'You do not have the required permissions.\r\n')

        def do_listrooms(self,session,line):
            #lists all rooms on the server
            session.push(LIST+self.server.list_rooms()+'\r\n')


        def do_joinroom(self,session,line):
            #for the user to join another room,format:joinroom room_name
            flag=0
            for ele in self.server.rooms:
                if ele.name==line.strip():
                    flag=1
                    session.enter(ele)
                    session.push(SERV+"Joined room %s"%ele.name)
            if not flag:
                session.push(ERR+'No such room,%s\r\n'%line.strip())

        def do_reqaddr(self,session,line):
            #request the ip address of another user,can be used for filesharing between clients
            if line.strip() in self.server.users:
                self.server.users[line.strip()].push_address(session)
            else:
                session.push(ERR+'User %s not found\r\n'%line.strip())
        def do_setmsg(self,session,line):
            if session.isAdmin:
                self.msg=line.strip()
                session.push(SERV+'Welcome message set\r\n')
            else:
                session.push(ERR+'You do not have the required permissions.\r\n')

        def do_statset(self,session,line):
            session.set_status(line)
            

        def do_fsetmsg(self,session,line):
            if session.isAdmin:
                try:
                    f=open(line.strip())
                    self.msg=f.read()
                except Exception,e:
                    session.push(ERR+str(e)+'\r\n')
                else:
                    session.push(SERV+'%s set as welcome message file\r\n'%line.strip())
            else:
                session.push(ERR+'You do not have the required permissions.\r\n')


        def play_welcome_message(self,session,msg):
            #plays welcome message when user enters the room
            session.push(MSG+msg)



    class LogoutRoom(Room):
        #used for logging the user out
        def add(self, session):
            try: del self.server.users[session.name]
            except KeyError: pass

    class ChatSession(async_chat):
        #Object identifying each user

        def __init__(self, server, sock,addr):

            async_chat.__init__(self, sock)
            self.server = server
            self.set_terminator("\r\n")
            self.data = []
            self.addr=addr[0]
            self.status = ''
            self.name=None
            self.isAdmin=False
            self.enter(LoginRoom(server))
            self.accept_file_flag=True
        def enter(self, room):
            #user enters a new room,quits the current room

            try: cur = self.room
            except AttributeError: pass
            else: cur.remove(self)
            self.room = room
            room.add(self)
        def set_status(self,status):
            self.status=status
        def push_address(self,session):
            #used for reqaddr command
            session.push(ADDR+(self.addr)+'\r\n')

        def collect_incoming_data(self, data):
            #reads data from user's socket

            self.data.append(data)

        def found_terminator(self):
            #the user's request is handled as soon as a line terminator is reached.

            line = ''.join(self.data)
            self.data = []
            try:
                self.room.handle(self,line)
            except EndSession:
                self.handle_close() #raised when logging out
        def handle_close(self):
            #destroys the session upon logging out
            #self.push(MSG+'Closing session\r\n')
            async_chat.handle_close(self)
            self.enter(LogoutRoom(self.server))





    class ChatServer(dispatcher):
        def __init__(self,port,name,max=5):
            dispatcher.__init__(self)
            self.log=''''''
            self.name=name
            self.sessions=[]
            self.rooms=[]
            self.admins={'root':'pw1'}
            #user/password(or hash) combinations,you can make the password a hash and
            #modify do_admin for more security

            self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
            self.set_reuse_addr()
            self.bind(('127.0.0.1',port))
            self.listen(max)
            self.users = {}

            self.rooms.append(ChatRoom(self,"Home"))


        def handle_accept(self):
            conn, addr = self.accept()
            y=ChatSession(self,conn,addr)

            self.sessions.append(y)
        def new_room(self,name):
            self.rooms.append(ChatRoom(self,name))
        def del_room(self,room):
            if len(self.rooms)>1:
                for i in range(len(self.rooms)):
                    if room==self.rooms[i].name:
                        for session in self.rooms[i].sessions:
                            session.handle_close()
                        del self.rooms[i]
        def whois(self):
            i=0
            for user in self.users:
                if i:
                    yield '::'
                yield user
                i=1
        def writelogs(self,file='logs.txt'):
            f=open(file,'a')

            f.write(self.log)
            f.close()
            self.log=''''''
        def list_rooms(self):
            str=''
            for room in self.rooms:
                str+=room.name+'\r\n'
            return str[:-1]





    s = ChatServer(7777,"pyzok chat server")



    try:

        asyncore.loop()

    except KeyboardInterrupt: pass

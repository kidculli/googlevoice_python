__author__ = 'clam'
"""
@author Cullin Lam

Created on 1/27/15

CHANGE LOG:
    2/6/15
        - get_sms returns today's date in str format instead of time received
    3/2/15
        - send_sms uses desktop url instead of mobile url
    6/2/15
        -log_in uses 'https://www.google.com/voice/#inbox' to get _rnr_se
        -get_sms uses 'https://www.google.com/voice/inbox/recent/inbox/' to get
        messages, uses both json and html to get message data
    

"""
# Python Modules
import requests
import datetime
import imp
import json
from bs4 import BeautifulSoup

#Import ASPYTHONLIB 
ASPYTHONLIB = imp.load_source('ASPythonLib',
                              '/app/as/lib/aspythonlib/ASPythonLibv2.py')
# Create Log Object
LOG = ASPYTHONLIB.Log()
LOG.Create('SMS class_googlevoice','dev',True)


class GoogleVoice(object):
    """
    This class initializes a googlevoice session. Allows the user to utilize
    googlevoice sms functions.
    """
    # Our credentials
    # class members

    #_rnr_se :  post parameter
    # Are we logged in already?
    #_logged_in = False

    def __init__(self, login, password):
        """
        Constructor method for GoogleVoice class. Sets login credentials.

        Args
            -"login (str)": a string containing googlevoice login username
            ="password(str)"" a string containing googlevoice login password
        Returns
            -None
        """
        self._login = login
        self._pass = password
        # Initialize server session object to maintain cookies
        self.session_obj = requests.Session()
        self._logged_in = False
        self._rnr_se = None

    def _log_in(self):
        """
        This function logs into googlevoice with the object credentials

        Args
            -None
        Returns
            -True(bool) if already logged in
        """
        if self._logged_in:
            return True
        login_url = 'https://accounts.google.com/ServiceLoginAuth?service=grandcentral'
        # Fetch login page
        self.session_obj.get(login_url)
        # get the GALX token that we need as a POST parameter to login
        galx_token = self.session_obj.cookies['GALX']
        # dictionary that holds our post parameters
        pay_load = {'GALX':galx_token, 'Email':self._login, 'Passwd': self._pass,
                    'service':'grandcentral&source=com.lostleon.GoogleVoiceTool'}
        # Send post request
        r = self.session_obj.post(login_url,data = pay_load)
        # Check for HTTP errors 
        if r.raise_for_status():
            LOG.error(str(requests.exceptions.HTTPError('Login http fail')))
        # Navigate to googlevoice page and get _rnr_se value
        page = self.session_obj.get('https://www.google.com/voice/#inbox')
        soup = BeautifulSoup(page.content)
        for i in soup.find_all('input'):
            if i.get('name') == '_rnr_se':
                self._rnr_se = i.get('value')
                break

        if self._rnr_se:
            print "Login succeeded! _rnr_se value:%s"%(self._rnr_se)
            self._logged_in = True
        else:
            raise Exception ("Could not log in to Google Voice with username: %s password: %s "
                             % (self._login, self._pass))

    def send_sms(self, number, message):
        """
        This function sends a sms message to the specified number

        Args
            "number(int)": The phone number of the receiver
            "message(str)": The message to send to the receiver
        Return
            -None
        """
        # Log into google voice
        self._log_in()
        # url address for sending sms
        send_url='https://www.google.com/voice/sms/send/'
        # post parameters for posting to the form
        pay_load = {'phoneNumber': number, 'id':'', 'text':message,
                    'sendErrorSms':0,'_rnr_se':self._rnr_se}
        r = self.session_obj.post(send_url, data=pay_load)
         # Check for HTTP errors 
        if r.raise_for_status():
            LOG.error(str(requests.exceptions.HTTPError('send_sms http fail')))

    def _convert_time(self,in_time):
        """
        This function takes a string containing hour and minute and
        converts it to the appropriate date time string using today's date.

        Args
            -'in_time(str)': string containing hour:minute AM/PM
        Returns
            -Datetime object
        """
        today = datetime.datetime.today()
        time_stamp=str(in_time)
        time_piece = time_stamp.split(':',1)
        the_hour=int(time_piece[0])
        the_min = int(time_piece[1][:2])
        if time_stamp.find('PM')!=-1:
            if the_hour == 12:
                pass
            else:
                the_hour += 12
        else:
            if the_hour == 12:
                the_hour = 0
        time_obj = datetime.datetime(year=today.year, day=today.day,
                                 month=today.month, hour=the_hour,
                                 minute=the_min)
        return time_obj.strftime('%d-%b-%y %H:%M:%S')

    def get_sms(self):
        """
        This function returns any unread messages as a list of dictionaries
        with keys: msgID, phoneNumber, message, datetime

        Args
            -None
        Return
            -list of dictionaries with messages
        """
        # Today's Date
        self._log_in()
        read_url = 'https://www.google.com/voice/inbox/recent/inbox/'
        page = self.session_obj.get(read_url)
        # Check for HTTP errors 
        if page.raise_for_status():
            LOG.error(str(requests.exceptions.HTTPError('get_sms http fail')))
        # Create BeautifulSoup object
        soup = BeautifulSoup(page.content,'xml')
        # Get the json tag
        json_string = str(soup.response.json)
        # Get beginning index of json string
        index= json_string.index('{"messages"')
        # Get ending index of json string
        index2= json_string.rindex('}')
        # Slice to get the json string
        real_json = json_string[index:index2+1]
        # Convert json into python object
        data = json.loads(real_json)
        soup = BeautifulSoup(page.content)
        html = soup.html
        message_list = []
        # Use msg id from json to search html for messages
        for msg_id in data['messages']:
            found = html.find('div',id=msg_id)
            # If div id not found, just use the json data
            if not found:
                m_data = data['messages'][msg_id]
                new_message={'msgID': msg_id,
                         'phoneNumber': m_data['phoneNumber'],
                         'message': m_data['messageText'],
                         'datetime':m_data['displayStartTime']}

                if new_message['phoneNumber']!='Me:':
                    # Transform phonenumber and datetime to applicable format
                    new_message['phoneNumber']=new_message['phoneNumber'][2:]
                    new_message['datetime']=self._convert_time(new_message[
                                                               'datetime'])
                    message_list.append(new_message)
            # Search html for the div id
            else:
                messages = found.find_all('div',class_='gc-message-sms-row')
                for message in messages:
                    elements = message.find_all('span')
                    new_message={'msgID': msg_id,
                             'phoneNumber': str(elements[0].text.strip().strip('\n')),
                             'message': str(elements[1].text).lstrip(),
                             'datetime':str(elements[2].text).strip().strip('\n')}

                    if new_message['phoneNumber']!='Me:':
                        # Transform phonenumber and datetime to applicable format
                        new_message['phoneNumber']=new_message['phoneNumber'][2:-1]
                        new_message['datetime']=self._convert_time(new_message[
                                                                   'datetime'])
                        message_list.append(new_message)

        return message_list

    def mark_msg_read(self, msg_id):
        """
        This function marks a message as read, use mark_msg_trash instead

        Args
            -"msg_id(str)": google voice identifier for a message
        Returns
            -None
        """
        self._log_in()
        mark_read_url='https://www.google.com/voice/inbox/mark/'
        pay_load={'messages': msg_id, 'read': 1, '_rnr_se': self._rnr_se}
        self.session_obj.post(mark_read_url, data=pay_load)

    def mark_msg_trash(self, msg_id):
        """
        This function marks a message as trash

        Args
            -"msg_id(str)": google voice identifier for a message
        Returns
            -None
        """
        self._log_in()
        mark_trash_url='https://www.google.com/voice/inbox/deleteMessages/'
        pay_load = {'messages': msg_id, 'trash': 1, '_rnr_se': self._rnr_se}
        r = self.session_obj.post(mark_trash_url, data=pay_load)
         # Check for HTTP errors 
        if r.raise_for_status():
            LOG.error(str(requests.exceptions.HTTPError('mark_msg_trash http fail')))

if __name__ == '__main__':
    gv = GoogleVoice("voice.test01845@gmail.com", "June2008")
    # print gv.get_sms()
    # for x in gv.get_sms():
    #     gv.mark_msg_trash(x['msgID'])
    print gv._convert_time('10:00 AM')

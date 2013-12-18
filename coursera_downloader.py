#!/usr/bin
#encoding=utf-8

import urllib
import urllib2
import cookielib
from bs4 import BeautifulSoup
import ConfigParser
#from termcolor import colored
from bcolors import bcolors
import utils

TIME_OUT = 60

class Downloader:

    HOME_URL  = 'https://www.coursera.org/'
    LOGIN_URL = 'https://accounts.coursera.org/api/v1/login'

    def __init__(self):
        self.cookiejar = cookielib.CookieJar()
        #HTTPHandler is not useful, we need HTTPSHandler
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar),urllib2.HTTPSHandler(debuglevel = 0))
        # addheaders is a list
        self.opener.addheaders = [('User-agent','Mozilla/4.0(compatible;MSIE 7.0;Windows NT 5.1)')]
        #self.opener.addheaders.append (('content-type','application/json'))
        csrftoken = self.csrfMake()
        self.opener.addheaders.append(('Cookie','csrftoken='+csrftoken))
        self.opener.addheaders.append(('Connection','keep-alive'))
        self.opener.addheaders.append(('X-CSRFToken',csrftoken))
        self.opener.addheaders.append(('X-Requested-With','XMLHttpRequest'))

    def print_cookies(self):
        print "\nPrinting cookies"
        for cookie in self.cookiejar:
            print cookie.name
            print cookie.value

    def csrfMake(self):
        """
        Generate csrftoken. Method idea is from csrfMake function in 
        https://d1rlkby5e91r2j.cloudfront.net/6931f8514c27ab9c02f964b79785ab3ef763a03e/pages/auth/routes.js
        """
        import random
        import math

        output = []
        length = 24
        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(length):
            output.append(chars[int(math.floor(random.random() * len(chars)))])
        output = ''.join(output)

        print "csrftoken =",output
        return output

    def open_page(self,url):
        request = urllib2.Request(url)
        try:
            response = self.opener.open(request).read()
            print bcolors.OKGREEN,url,"Open Success!",bcolors.ENDC
            return response
        except Exception:
            print bcolors.FAIL,url,"Open Error!",bcolors.ENDC
            return None

    #def open_home(self):
    #    return self.open_page(self.HOME_URL)

    def login(self, email, password):
        params = {
            "email":email,
            "password":password
            }

        request = urllib2.Request(self.LOGIN_URL)
        try:
            self.opener.open(request, urllib.urlencode(params))
            print bcolors.OKGREEN,"Login Success!",bcolors.ENDC
        except Exception,e:
            print bcolors.FAIL,e,bcolors.ENDC
            print bcolors.FAIL,"Login Error!",bcolors.ENDC

    def is_download_file(self, a):
        t = a['title'];
        return {
            'Discuss': False,
            'YouTube': False,
            'Article Audio Podcast': False,
            'Notes': False
        }.get(t, True)    # 9 is default if x not found

    def get_item_list(self, state, page, week_begin = None, week_end = None): 
        """
        min of week_begin should be 1 
        """

        week_begin = None if len(week_begin) == 0 else int(week_begin)
        week_end = None if len(week_end) == 0 else int(week_end)

        item_l = []
        soup = BeautifulSoup(page)
        if state == "unviewed":
            v_l = soup.find_all(class_ = "unviewed")
        elif state == "viewed":
            v_l = soup.find_all(class_ = "viewed")
        elif state == "all":
            v_l = []
            if week_begin and week_end:
                temp = soup.find_all(class_ = "course-item-list-section-list")[week_begin - 1:week_end]
            elif week_begin:
                temp = soup.find_all(class_ = "course-item-list-section-list")[week_begin - 1:-1]
            elif week_end:
                temp = soup.find_all(class_ = "course-item-list-section-list")[0:week_end]
            else:
                temp = soup.find_all(class_ = "course-item-list-section-list")
            for t in temp:
                v_l = v_l + t.find_all('li')

        print "item_section count",len(v_l)
        
        for i in v_l:
            res = i.find(class_ = "course-lecture-item-resource")
            if not res:
                continue
            for a in res.find_all('a'):
                #pdf: title = "***.pdf"
                #srt: title = "Subtitles(srt)"
                #txt: title = "Subtitles(txt)"
                #video:title = "Video(MP4)"
                if self.is_download_file(a):
                    item_l.append(a['href'])

        return item_l

    def download(self, video_url, save_dir, state, begin, end):
        page = self.open_page(video_url)
        items = self.get_item_list(state,page, begin, end)
        item_num = len(items)
        print "Item count is",item_num
        if item_num == 0:
            return

        i = 0
        while True:
            if self.save(items[i], save_dir):
            #import time
            #time.sleep(5)
                i+=1
            if i >= item_num:
                break

        print "Finish!"

    def extract_filename(self, item_url, res):
        # If the save_name is not specified, get save_name of this file.
        # If header of the response contents Content_Disposition, the filename is usually in there.
        # But if there's no filename in Content_Disposition, it maybe in url
        # else if the response's url is not the same as item_url, which means we are rediredcted, 
        # the real filename we take from the final URL
        # else extract name directly from item_url

        if res.info().has_key('Content-Disposition'):
            try:
                save_name = res.info()['Content-Disposition'].split('filename')[1]
                save_name = save_name.split('"')[1]
            except:
                save_name = item_url.split('?')[0].split('/')[-1]
        elif res.url != item_url:
            # if we were redirected, the real file name we take from the final URL
            from os.path import basename
            from urlparse import urlsplit
            save_name = basename(urlsplit(res.url)[2])
        else:
            #extract name directly from item_url
            save_name = item_url.split('/')[-1]
        try:
            #For the name in url, urldecode is usually necessary
            save_name = urllib.unquote(save_name.strip()).encode('latin1')
        except Exception:
            save_name = urllib.unquote(save_name.strip())

        save_name = save_name.replace('/','-')

        return save_name

    def save(self,item_url, save_dir, save_name=None):
        import os

        try:
            request = urllib2.Request(item_url)
            res = self.opener.open(request, timeout = TIME_OUT)
            if not save_name:
                save_name = self.extract_filename(item_url, res)

            if not os.path.exists(save_dir):
                os.mkdir(save_dir)

            if not save_dir.endswith('/'):
                save_dir = save_dir+'/'

            print bcolors.OKGREEN,"==========================================",bcolors.ENDC
            print bcolors.OKGREEN,"Downloading...",save_name,bcolors.ENDC

            #Check if the file has already been downloaded
            if os.path.exists(save_dir+save_name):
                print bcolors.WARNING,save_name,"has already been downloaded.",bcolors.ENDC
                res = None
                return True

            with open(save_dir+save_name,'w') as f:
                if res.info().has_key('Content-Length'):
                    file_size = int(res.info().getheader('Content-Length').strip())
                    print bcolors.OKGREEN,"Total",utils.file_size(file_size),bcolors.ENDC
                    file_size_dl = 0
                    block_sz = 1024*128
                    while True:
                        buffer = res.read(block_sz)
                        if not buffer:
                            break

                        file_size_dl += len(buffer)
                        f.write(buffer)
                        status = r"%s [%3.2f%%]" % (utils.file_size(file_size_dl), file_size_dl * 100. / file_size)
                        status = status + chr(8)*(len(status)+1)
                        print bcolors.OKGREEN,status,bcolors.ENDC
                else:
                    f.write(res.read())

            print bcolors.OKGREEN,save_name,"is OK",bcolors.ENDC
            return True

        except urllib2.URLError,e:
            print item_url," Error";
            print e
            print bcolors.FAIL,item_url,"Timeout",bcolors.ENDC
            if not save_name:
                return True
            if save_name and os.path.exists(save_dir+save_name):
                print bcolors.FAIL,save_name,"has been deleted.",bcolors.ENDC
            res = None
            return False

    def get_params(self, config_file):
        """
        Get the config parameters in config_file
        str -> dict
        """
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        return dict(config.items('Coursera'))

    def start(self, config_file):
        """
        The parameters are in config_file, which is "cousera.cfg"
        """
        #self.open_home()
        params = self.get_params(config_file)
        self.login(params['email'], params['password'])
        self.download(params['course_video_url'], params['save_dir'], params['state'], params['week_begin'], params['week_end'])
        
if __name__ == '__main__':
    d = Downloader()
    d.start('coursera.cfg')

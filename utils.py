#!/usr/bin
#encoding=utf-8

def file_size(byte):
    num = byte
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f%s"%(num,x)
        num /= 1024.0

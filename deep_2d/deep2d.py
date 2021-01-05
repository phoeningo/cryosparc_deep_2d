import os
import sys
import time
import thread
import json
import subprocess

sys.path.append('/cryoprograms/cryosparc/cryosparc2_master/')
from cryosparc2_compute.client import CommandClient

cli = CommandClient('syg2', 39002)

import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--input',type=str)
parser.add_argument('--pid',type=str,default='P1')
parser.add_argument('--wid',type=str,default='W2')
parser.add_argument('--mode',type=str,default='child')
parser.add_argument('--k',type=int,default=5)
parser.add_argument('--num_thre',type=int,default=100000)
parser.add_argument('--heartbeat',type=int,default=10)
parser.add_argument('--depth',type=int,default=2)
parser.add_argument('--project_path',type=str,default='/data/20201123_Congye_P3L/P1/')
args=parser.parse_args()


num_thre=args.num_thre
def check_state():
  try:
    state=os.popen('cryosparcm cli \' get_job_status("'+args.pid+'","'+args.input+'")  \'').read().split('\n')[0]
    if len(state)>3: 
      return state
    else:
      print state
      return 'error'
  except:
    return 'error'


def get_particles():
  try:
    return int(j['output_results'][0]['num_items'][0])
  except:
    return 0

#2d 
def queue_class2d(jid,knum):
  new_jobid=os.popen('cryosparcm cli \'make_job ("class_2D","'+args.pid+'","'+args.wid+'","",None,None,{"compute_use_ssd":"False","class2D_K":"'+str(knum)+'"},{"particles":"'+jid+'.particles_selected"})\'').read().split('\n')[0]
  #sub_pro=subprocess.
  os.system('cryosparcm cli \' enqueue_job("'+args.pid+'","'+new_jobid+'","default")   \'')
  state=''
  while(state!='completed'):
    time.sleep(args.heartbeat*6)
    state=os.popen('cryosparcm cli \' get_job_status("'+args.pid+'","'+new_jobid+'")  \'').read().split('\n')[0]
  #sub_pro.communicate()
  return new_jobid

def queue_select2d(djid,idx):
  
  new_jobid=os.popen('cryosparcm cli \'make_job ("single_select","'+args.pid+'","'+args.wid+'","",None,None,{"class_idx":"'+str(idx)+'","particle_count_above":"'+str(num_thre)+'"},{"particles":"'+djid+'.particles","templates":"'+djid+'.class_averages"})\'').read().split('\n')[0]
  os.popen('cryosparcm cli \' enqueue_job("'+args.pid+'","'+new_jobid+'","default")   \'')
  os.system('sh ~/bin/run.sh '+new_jobid)
  print('sh ~/bin/kongfang_packages/run.sh '+new_jobid)
  waiting_list.pop() 
  return 



waiting_list=[]
K=args.k
j={}
if args.mode=='child':
  print('one job come in :'+args.input)
#checkfirst
  input_job=args.input.split('.')[0]
  while(check_state()!='completed'):
    print('Queued beacause Current Inputs are not avaliable.') 
    print('Job '+args.input+' status: '+check_state())
  # status like killed may throw exception
    time.sleep(args.heartbeat)
  
  fp=open(args.project_path+'/'+args.input+'/job.json')
  j=json.load(fp)
  fp.close() 
  fp=0

# check particle number
  if get_particles()<=num_thre:
    print('Too few particles,stop now.')
    sys.exit(1)
  else:
  # determin K number according to particles number
    K=get_particles()*4/args.num_thre
    print(K)
    #print(get_particles())
    JID=queue_class2d(args.input,K)
else:
  JID=args.input


if len(JID.split('J'))!=2:
  print('Error Job got!'+JID)
  sys.exit(1)
 
for i in range(K):
  waiting_list.append('Job_x')
  thread.start_new_thread(queue_select2d,(JID,i))
  #queue_select2d(JID,i)
 
while(waiting_list!=[]):
#while(1):
  pass
  #time.sleep(10)

print('all job queued.')
      
  

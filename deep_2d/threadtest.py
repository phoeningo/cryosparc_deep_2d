import thread  

import time

current_job_count=0
max_job_num=4

job_queue=[]


def queue_job(tid):
  job_queue.insert(0,tid)
  print('current job queue: ')
  print(job_queue)



def print_time(tid,delay):
  count=0
  while count<5:
    time.sleep(delay)
    count+=1
    print("%s : %s "% (tid,time.ctime(time.time())))
  print('End')

  #current_job_count+=1
  #queue_job("Thread"+str(current_job_count))
  working_stack.remove(tid)
  return


#init job queue
for i in range(max_job_num):
  current_job_count+=1
  queue_job("Thread"+str(current_job_count))


working_stack=[]

def new_thread():
  while( len(working_stack)>max_job_num):
    print('waiting for current running jobs ...')
    time.sleep(3)
  tid=job_queue.pop()
  thread.start_new_thread( print_time, (tid, 2, ) )
  print('Excute : '+tid)
  working_stack.append(tid)




while (1):
  try:
    if job_queue!=[]:
      for t in job_queue:
        new_thread()
    elif working_stack==[]:
      print('no job in queue and no job running,exit now.')
      break
    else:
      print('no jobs in queue ,but there remains job running.waiting..')
      time.sleep(5)
      
  except:
     print "Error: unable to start thread"




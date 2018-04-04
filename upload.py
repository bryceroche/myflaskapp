
import datetime
import os
from random import randint
import csv

UPLOAD_FOLDER = '/Users/bryceroche/desktop/myflaskapp'
ALLOWED_EXTENSIONS = set(['txt', 'csv'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(request, session, mysql):
    filename = step1(request)
    rand = random_number()
    session['batchid'] = rand
    userid = session['userid']

    print filename, rand, userid
    data = prepare_insert(rand, userid, filename)
    printstuff(data)
    add_user(data, mysql)
    os.remove(filename)

def printstuff(arr):
    for a in arr:
        print a
def step1(request):
    file = request.files['file']
    if file and allowed_file(file.filename):
        now = datetime.datetime.now()
        filename = os.path.join(UPLOAD_FOLDER, "%s.%s" % (now.strftime("%Y-%m-%d-%H-%M-%S-%f"), file.filename.rsplit('.', 1)[1]))
        file.save(filename)
        return str(filename)

def random_number():
    return randint(0, 10000000)

def prepare_insert(random_number, userid, filename):
    abc = build_insert(filename)
    if (abc[0][0]=='First Name'):
      abc.pop(0)

    abc = add_col(abc, userid)
    abc = add_col(abc, random_number)
    abc = add_col(abc, filename)
    return abc

def add_col(newarr, extrafield):
  #add column to list subtract xxx minutes from end time
  return [x + [extrafield] for x in newarr]


def add_user(data, mysql):
    cur = mysql.connection.cursor()
    sql = "insert into users (fname, lname, emailaddress, mobilenumber, companyname, rolename, upload_user, batchid, filename) values(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    number_of_rows = cur.executemany(sql, data)
    mysql.connection.commit()
    cur.close()
    print number_of_rows

def build_message(templateid, batchid):
  template1 = get_data('api_batch_email1', [templateid])
  themap = get_data('api_msg_template_sub', [templateid])
  thedata = get_data('api_batch_email2', [batchid])

  template2 = template1[0][1]
  subject = template1[0][7]
  print subject

  for a in thedata:
    newmsg = template2
    for b in themap:
      index1 = b[5]
      newmsg = newmsg.replace(b[2], a[index1])
    send_one_email(a[0], newmsg, subject) # send email
    get_data('api_set_log', [a[4], 1, templateid, 1]) # write to log table #userid, msg_type (email/sms), templateid, companyid


def get_data(mysql, spname, data):
    print 'in the get_data', spname, data
    cur = mysql.connection.cursor()
    cur.callproc(spname, data)
    result_set = cur.fetchall()
    #mysql.connection.commit()
    cur.close()
    return result_set



def begin_here(s1, s2):
  templateid = int(s1)
  batchid = int(s2)
  print templateid, batchid

  a = get_data('api_email_encrypt', []) # this syncs the email_encrpyt table with users
  build_message(templateid, batchid)


def build_insert(filename):
  results = []
  with open(filename) as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
      results.append(row)
  return results





"""
def send_one_email(theemail, msg, thetitle):
    client = boto3.client('ses')

    response = client.send_email(
        Destination={
            'BccAddresses': [
            ],
            'ToAddresses': [
                theemail,
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': msg,
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': msg,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': thetitle,
            },
        },
        Source='support@adri-sys.com',
    )
"""

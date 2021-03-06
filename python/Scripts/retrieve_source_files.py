import logging
import boto3
from botocore.exceptions import ClientError
import requests
import wget
import tempfile
import io
import pandas as pd
import zipfile


def upload_file(url, bucket, profile='default'): 
    
    """Upload a file to an S3 bucket
    :param url: URL to file location
    :param bucket: Bucket to upload to
    :param profile: identify which credentials you want to use
    :return: True if file was uploaded, else False
    """
    
    #Create list of url to pull zip from
    try:
        s = requests.get(url).content
        targets = pd.read_csv(io.StringIO(s.decode('utf-8')))
    except:
        return (f'ERROR please check that you have the correct url: {url}')
        
    #If no profile specified use default
    boto3.setup_default_session(profile_name=profile) 
    
    #iterate through list of url and download zip
    for index, row in targets.iterrows():
        with tempfile.TemporaryDirectory() as tmpdirname:
            print("Retrieving " + row['Zip File Name'])
            wget.download(row['Direct URL'], tmpdirname + "/" + row['Zip File Name'], bar=None)
            print("Downloaded "+ row['Zip File Name'])
            s3_client = boto3.client('s3')
            try:
                s3_client.upload_file(tmpdirname + "/" + row['Zip File Name'], bucket, row['Zip File Name'])
            except ClientError as e:
                logging.error(e)
    unzip(bucket, profile)


def unzip(bucket, profile='default'):
    #setting up environment specifying profile to use
    boto3.setup_default_session(profile_name = profile)

    #initializing s3_resource, s3_client, paginator
    s3_resource = boto3.resource('s3')
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator("list_objects_v2")

    zip_files = []

    for page in paginator.paginate(Bucket=bucket):
        for obj in page['Contents']:
            if obj['Key'].endswith('.zip'):
                zip_files.append(obj['Key'])
            else:
                pass

    if len(zip_files) > 0:
        print(zip_files)
        for key in zip_files:
            zip_obj = s3_resource.Object(bucket_name=bucket, key=key)
            buffer = io.BytesIO(zip_obj.get()["Body"].read())
            z = zipfile.ZipFile(buffer)
            for filename in z.namelist():
                file_info = z.getinfo(filename)
                s3_resource.meta.client.upload_fileobj(
                    z.open(filename),
                    Bucket=bucket,
                    Key = f'{key[:-4]}/{filename}')
            s3_resource.Object(bucket, key).delete()
        unzip(bucket)
    else:
        print('Finished')


# if __name__ == "__main__":
#     upload_file('https://raw.githubusercontent.com/stlrda/redb_python/master/config/redb_source_databases_urls.csv', 'amtestbucket11')
    # unzip('amtestbucket11')
import os
import mimetypes
import boto3

s3_bucket = os.environ.get("S3_BUCKET", "makumistake")
S3 = boto3.client("s3")
s3_bucket_location = "us-east-2"


def s3_stuff(prefix="/", delimiter="/", start_after=""):
    s3_paginator = boto3.client("s3").get_paginator("list_objects_v2")
    prefix = prefix[1:] if prefix.startswith(delimiter) else prefix
    start_after = ((start_after or prefix) if prefix.endswith(delimiter)
                   else start_after)
    for page in s3_paginator.paginate(Bucket=s3_bucket,
                                      Prefix=prefix,
                                      StartAfter=start_after):
        for content in page.get("Contents", ()):
            yield content


def url_from_s3_key(s3_key):
    url = (f"https://{s3_bucket}.s3.{s3_bucket_location}"
           f".amazonaws.com/{s3_key}")
    return url


def fix_metadata(s3_key, new_mimetype):
    print(f"Setting {s3_key} to {new_mimetype}...")
    S3.copy_object(Bucket=s3_bucket,
                   Key=s3_key, CopySource=f"{s3_bucket}/{s3_key}",
                   MetadataDirective="REPLACE",
                   ACL='public-read',
                   ContentType=new_mimetype)


contents = list(s3_stuff(prefix="pictures/"))
print(f"{len(contents)=}")
# contents = contents[:100]
print(f"{len(contents)=}")
heads = [S3.head_object(Bucket=s3_bucket, Key=content["Key"])
         for content in contents]
print(f"{len(heads)=}")
urls = [url_from_s3_key(content["Key"]) for content in contents]
guessed_mimetypes = [mimetypes.guess_type(url)[0] for url in urls]
actual_mimetypes = [head["ContentType"] for head in heads]
mimetypes_accurates = [guessed_mimetypes[i] == actual_mimetypes[i]
                       for i in range(len(guessed_mimetypes))]
incorrect_indeces = [i for i in range(
    len(mimetypes_accurates)) if not mimetypes_accurates[i]]
incorrect_guessed_mimetypes = [guessed_mimetypes[i] for i in incorrect_indeces]
incorrect_actual_mimetypes = [actual_mimetypes[i] for i in incorrect_indeces]
incorrect_urls = [urls[i] for i in incorrect_indeces]
incorrect_heads = [contents[i]["Key"] for i in incorrect_indeces]

print(f"Starting {len(incorrect_indeces)} corrections...")

for i in incorrect_indeces:
    incorrect_key = contents[i]["Key"]
    new_mimetype = guessed_mimetypes[i]
    if new_mimetype:
        fix_metadata(incorrect_key, new_mimetype)

#!/bin/sh

if [ $# -ne 4 ]
then
  echo "Usage: $0 HOSTED_NAME DNS_NAME DNS_IP/DNS_NAME RECORD_TYPE"
  exit 1
fi

# Get the hosted-zone-id from the hosted-zone-name $1
HOSTED_ZONE_NAME=$1

HOSTED_ZONE=`aws route53 list-hosted-zones-by-name --dns-name $1 | python3 -c "import sys, json; print(json.load(sys.stdin).get('HostedZones', {})[0].get('Id'))"`

if [ $? -ne 0 ]
then
   exit 2
fi

echo "Hosted zone id : $HOSTED_ZONE"

# Get the DNS entry that we want to change
DNS_NAME=$2

echo "DNS Entry to change: $DNS_NAME"

# Get the value of the ip to set
DNS_IP=$3

echo "IP/DNS_NAME to be set: $DNS_IP"

# Set the record type 'A' for EC2 and 'CNAME' for RDS
RECORD_TYPE=$4

echo "TYPE of Record to be set: $RECORD_TYPE"

cat <<EOF >req.json
{
  "Comment": "Pygmy Update",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DNS_NAME",
        "Type": "$RECORD_TYPE",
        "TTL": 60,
        "ResourceRecords": [
          {
            "Value": "$DNS_IP"
          }
        ]
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE --change-batch file://req.json
output=$?

# Delete request file
rm req.json

# Exit Script
exit $output

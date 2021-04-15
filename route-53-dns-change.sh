#!/bin/sh

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

echo "IP to be set: $DNS_IP"

cat <<EOF >req.json
{
  "Comment": "Pygmy Update",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DNS_NAME",
        "Type": "A",
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

exit $?

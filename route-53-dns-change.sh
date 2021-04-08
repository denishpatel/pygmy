#!/bin/sh

# Get the hosted-zone-id from the client $1
HOSTED_ZONE=$1

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

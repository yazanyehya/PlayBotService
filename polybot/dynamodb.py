import boto3
import uuid
from typing import List, Dict, Optional
from boto3.dynamodb.conditions import Key
import os
SESSION_TABLE = os.getenv("SESSION_TABLE")
OBJECT_TABLE = os.getenv("OBJECT_TABLE")

class DynamoDBStorage():
    def __init__(self, region="us-west-1"):
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.sessions_table = self.dynamodb.Table(SESSION_TABLE)
        self.objects_table = self.dynamodb.Table(OBJECT_TABLE)

    def get_prediction(self, uid: str) -> Optional[Dict]:
        print(f"🔍 Fetching prediction session with uid={uid}")
        response = self.sessions_table.get_item(Key={"uid": uid})
        print(f"Reponse :",response)

        session = response.get("Item")
        print("Session:",session)
        if not session:
            print("❌ No session found.")
            return None

        print("✅ Session found:", session)

        try:
            objects_response = self.objects_table.query(
                IndexName="prediction_uid-index",
                KeyConditionExpression=Key("prediction_uid").eq(uid)
            )
            objects = objects_response.get("Items", [])
            print(f"🟢 Found {len(objects)} detection objects for uid={uid}")
        except Exception as e:
            print(f"❌ Failed to query detection objects: {e}")
            objects = []

        session["detection_objects"] = objects
        return session
import boto3

def get_dynamodb_item(table_name, key):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    response = table.get_item(
        Key=key
    )

    item = response.get('Item')
    return item

# Example usage
table_name = 'YourTableName'
key = {
    'YourPrimaryKeyName': 'YourPrimaryKeyValue'
}

result = get_dynamodb_item(table_name, key)

if result:
    print("Item found:", result)
else:
    print("Item not found.")

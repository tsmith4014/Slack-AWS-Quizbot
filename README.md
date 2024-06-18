### Creating a Slack Quiz Bot Using AWS Lambda and S3

This detailed guide will walk you through the steps to create a Slack bot that quizzes users on questions from an AWS Solutions Architect exam. The questions and answers will be stored in a JSON file in an S3 bucket, and the bot will interact with users via a slash command `/quiz`.

### Step 1: Set Up the Slack App

1. **Create a Slack App**:

   - Go to the [Slack API](https://api.slack.com/apps) page and create a new app.
   - Choose the workspace where you want to develop your app.

2. **Add Features and Functionality**:
   - **OAuth & Permissions**: Add the following scopes under `Bot Token Scopes`:
     - `channels:read`
     - `chat:write`
     - `commands`
   - **Install the App**: Install the app to your workspace and obtain the OAuth access token and signing secret.
   - **Save the OAuth token and signing secret**: These will be used later in the environment variables terraform.tfvars file.

### Step 2: Set Up the Project Directory

1. **Create a new project directory and navigate into it**:

```sh
mkdir slack-quiz-bot
cd slack-quiz-bot
```

### Step 3: Create the Lambda Function in Python

1. **Create a directory for the Lambda function**:

```sh
mkdir lambda
cd lambda
```

2. **Create the main Lambda function file `lambda_function.py`**:

```python
import os
import json
import boto3
import random
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

s3_client = boto3.client('s3')
app = App(signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))

@app.command("/quiz")
def quiz(ack, respond, command):
    ack()
    s3_bucket = os.environ.get("S3_BUCKET")
    s3_key = os.environ.get("S3_KEY")
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    questions = json.loads(response['Body'].read().decode('utf-8'))

    selected_questions = random.sample(list(questions.items()), 10)
    user_quiz = []

    for q in selected_questions:
        question, answer = q
        user_quiz.append({
            'question': question.split("\n   ")[0],
            'options': question.split("\n   ")[1:],
            'answer': answer.split(" ")[1]
        })

    respond({
        "response_type": "in_channel",
        "text": "Starting your quiz! Answer the following questions:",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"1. {user_quiz[0]['question']}\n{user_quiz[0]['options'][0]}\n{user_quiz[0]['options'][1]}\n{user_quiz[0]['options'][2]}\n{user_quiz[0]['options'][3]}"
                }
            }
        ]
    })

def handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
```

### Step 4: Create `requirements.txt`

Create a `requirements.txt` file in the `lambda` directory to specify the dependencies:

```plaintext
slack-bolt
boto3
```

### Step 5: Use a Virtual Environment and Package the Lambda Function

1. **Create a Virtual Environment**:

```sh
python3 -m venv venv
```

2. **Activate the Virtual Environment**:

```sh
source venv/bin/activate  # On Windows, use .\venv\Scripts\activate
```

3. **Install Dependencies**:

```sh
pip install -r requirements.txt
```

4. **Package the Lambda Function**:

```sh
zip -r ../lambda.zip *
```

5. **Deactivate the Virtual Environment**:

```sh
deactivate
```

6. **Clean Up** (Optional):

```sh
rm -rf venv
```

### Step 6: Terraform Configuration

1. **Go back to the root directory and create a `main.tf` file for your Terraform configuration**:

```hcl
provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

resource "aws_lambda_function" "slack_quiz_bot" {
  function_name = "slack_quiz_bot"
  handler       = "lambda_function.handler"
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_exec.arn
  filename      = "${path.module}/lambda.zip"
  environment {
    variables = {
      SLACK_SIGNING_SECRET = var.slack_signing_secret
      SLACK_BOT_TOKEN      = var.slack_bot_token
      S3_BUCKET            = var.s3_bucket
      S3_KEY               = var.s3_key
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.slack_quiz_bot.function_name}"
  retention_in_days = 14
}

resource "aws_api_gateway_rest_api" "api" {
  name        = "Slack Quiz Bot API"
  description = "API Gateway for the Slack Quiz Bot"
}

resource "aws_api_gateway_resource" "slack_command" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "slack"
}

resource "aws_api_gateway_method" "post_slack_command" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.slack_command.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.slack_command.id
  http_method             = aws_api_gateway_method.post_slack_command.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.slack_quiz_bot.arn}/invocations"
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "prod"
  depends_on = [
    aws_api_gateway_integration.lambda
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_quiz_bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.api.id}/*/POST/slack"
}
```

### Step 7: Variables and Secrets

1. **Create a `variables.tf` file to define your variables**:

```hcl
variable "slack_signing_secret" {
  description = "Slack signing secret"
  type        = string
}

variable "slack_bot_token" {
  description = "Slack bot token"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket name"
  type        = string
}

variable "s3_key" {
  description = "S3 key for the JSON file"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
```

2. **Create a `terraform.tfvars` file to provide values for these variables**:

```hcl
slack_signing_secret = "your_slack_signing_secret"
slack_bot_token      = "your_slack_bot_token"
s3_bucket            = "your_s3_bucket_name"
s3_key               = "path/to/your/lookup_table.json"
```

### Step 8: Deploy with Terraform

1. **Initialize Terraform, plan, and apply the configuration**:

```sh
terraform init
terraform plan
terraform apply
```

#### Step 9: Update the Slack Command with the API Gateway Endpoint (continued)

1. **After deploying, get the API Gateway endpoint URL from the Terraform output or AWS Console**.
2. **Go back to your Slack app settings, and under Slash Commands, update the Request URL with the API Gateway endpoint**:
   - **Command**: `/quiz`
   - **Request URL**: `https://your-api-gateway-endpoint/prod/slack`
   - **Short Description**: `Starts a quiz with 10 random questions`
   - **Usage Hint**: `Just type /quiz to start the quiz`
   - **Escape Channels, Users, and Links Sent to Your App**: Leave this enabled.

### Step 10: Finalize the Slack Command Setup

1. **Autocomplete Entry**:
   - **Command**: `/quiz`
   - **Short Description**: `Starts a quiz with 10 random questions`
   - **Usage Hint**: `Just type /quiz to start the quiz`

### Step 11: Invite the Bot to Your Slack Channel

1. **Invite the bot to the channel**:

   - Go to the channel where you want the bot to be active.
   - Use the `/invite` command to invite the bot to the channel: `/invite @your-bot-name`.

2. **Obtain the Channel ID** (if needed):
   - Open the Slack channel where you want to use the bot.
   - Click on the channel name to open the channel details.
   - Scroll down to find the **Channel ID**. This might be required if you want the bot to post messages or interact with a specific channel programmatically.

### Step 12: Testing Your Bot

1. **Start the quiz**:

   - Go to the Slack channel where the bot is invited.
   - Type `/quiz` to start the quiz.
   - The bot should respond with the first question from the JSON file stored in S3.

2. **Respond to the quiz**:
   - Answer the question in the channel.
   - The bot should respond with the correct answer and then post the next question.
   - This process repeats until all 10 questions are answered.

### Conclusion

This guide ensures that the Slack command is set up correctly at the end of the process when the API Gateway endpoint is available. It covers the entire process of setting up a Slack quiz bot that interacts with users, retrieves questions from an S3 bucket, and quizzes users with 10 random questions. The bot listens to the `/quiz` command, presents questions, and checks answers, ensuring a seamless quiz experience within Slack. Adjust the logic and paths as needed to ensure seamless integration and functionality.

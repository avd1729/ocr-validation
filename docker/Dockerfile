FROM public.ecr.aws/lambda/python:3.11

# Install Poppler for pdf2image (required)
RUN yum install -y poppler-utils && yum clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["main.handler"]

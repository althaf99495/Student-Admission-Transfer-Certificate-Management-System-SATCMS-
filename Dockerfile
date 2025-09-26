# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install GTK dependencies for WeasyPrint
RUN apt-get update && apt-get install -y libgobject-2.0-0 libpango-1.0-0 gir1.2-pango-1.0

# Copy the requirements file and install dependencies
COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5001

# Set the command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "wsgi:app"]

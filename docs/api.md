# API Documentation

## Health Endpoint

**GET /api/health**  
- **Description**: Check the status of the service.  
- **Response**:  
  - 200 OK: Service is running.

## Collect Endpoint

**POST /api/collect**  
- **Description**: Collects data from specified sources.  
- **Parameters**:  
  - `source` (string): The source from which to collect data.
- **Response**:  
  - 202 Accepted: Data collection initiated.

## Analyze Endpoint

**POST /api/analyze**  
- **Description**: Analyze collected data.  
- **Parameters**:  
  - `data` (object): The data to be analyzed.
- **Response**:  
  - 200 OK: Analysis results returned.

## Process Text Endpoint

**POST /api/process-text**  
- **Description**: Processes the input text data.  
- **Parameters**:  
  - `text` (string): The text to process.
- **Response**:  
  - 200 OK: Processed text results returned.

## Report Endpoint

**GET /api/report**  
- **Description**: Generate a report based on collected and analyzed data.  
- **Parameters**:  
  - `reportType` (string): Type of report to generate.
- **Response**:  
  - 200 OK: Report generated successfully.
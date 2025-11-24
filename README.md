$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-9.2.1-windows-x86_64.zip -OutFile elastic-agent-9.2.1-windows-x86_64.zip 
Expand-Archive .\elastic-agent-9.2.1-windows-x86_64.zip -DestinationPath .
cd elastic-agent-9.2.1-windows-x86_64
.\elastic-agent.exe install --url=https://localhost:8220 --enrollment-token=SmFqUHM1b0JLSmZDQl9faHhJTEs6V2JPN0xrWGx4ZDVJU2hlZHNadGw4QQ==

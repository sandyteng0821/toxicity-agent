# In Python shell or temporary test file
from app.services.json_io import read_json, write_json

data = read_json()
print(data.get("inci"))  # Should print "INCI_NAME" or your current value
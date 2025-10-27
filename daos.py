class InMemoryDao:
    def __init__(self):
        self.data = None

    def save_raw_data(self, data):
        self.data = data

    def retrieve_raw_data(self):
        return self.data

class FileDao:
    def __init__(self, file_name):
        InMemoryDao.__init__(self)
        self.file_name = file_name

    def save_raw_data(self, data):
        try:
            with open(self.file_name, "w") as storage_file:
                storage_file.write(data)
        except Exception as e:
            print("Failed to save configuration to file:", e)

    def retrieve_raw_data(self):
        try:
            with open(self.file_name, "r") as storage_file:
                file_content = storage_file.readlines()
                #print(f"file_content: {file_content}")
                if len(file_content) > 1:
                    print(f"Warning: found {len(file_content)} lines in storage file for wifi config. Expected was 1.")
                if len(file_content) == 0:
                    # No config found
                    return ""
                return file_content[0]
        except Exception as e:
            print("Failed to read wifi config file:", e)
            return ""
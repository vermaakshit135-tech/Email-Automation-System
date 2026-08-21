import pandas as pd

df = pd.read_csv(contact_file)

print(df)
for index, row in df.iterrows():
    name = row["name"]
    email = row["email"]

    print("Name:", name)
    print("Email:", email)
    print("----------------")
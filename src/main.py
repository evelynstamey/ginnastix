from utils.google_sheets import append_dataset_rows
from utils.google_sheets import authenticate
from utils.google_sheets import read_dataset

if __name__ == "__main__":
    creds = authenticate()
    df = read_dataset(dataset_name="skill_evaluation", credentials=creds)

    new_df = df.iloc[[0]]
    append_dataset_rows(dataset_name="skill_evaluation", df=new_df, credentials=None)

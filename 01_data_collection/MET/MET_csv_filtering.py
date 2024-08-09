import pandas as pd

file_path = 'MET_collections.csv' 
data = pd.read_csv(file_path)

filtered_paintings = data[(data['classification'] == 'Paintings') & 
                           (data['isPublicDomain'] == True) & 
                           (data['primaryImage'].notna())]

output_file_path = 'MET_paintings.csv'
filtered_paintings.to_csv(output_file_path, index=False)

print(f"Filtered data saved to {output_file_path}. Total paintings filtered: {len(filtered_paintings)}")

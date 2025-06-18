import pandas as pd

# Function to generate USPS-compatible address
def generate_usps_address(addr1, addr_extra, city, state, postalcode):
    parts = [addr1.strip(), addr_extra.strip()]
    street_line = " ".join([part for part in parts if part])
    location_line = f"{city.strip()}, {state.strip()} {postalcode.strip()}"
    return f"{street_line}, {location_line}"

# Load CSV file
input_file = "input.csv"   # <-- Replace with your actual file name
output_file = "usps_addresses_by_id.csv"

# Read the CSV
df = pd.read_csv(input_file)

# Generate USPS-compatible primary address
df["usps_address"] = df.apply(
    lambda row: generate_usps_address(
        str(row.get("address1", "")),
        str(row.get("address3", "")),
        str(row.get("city", "")),
        str(row.get("state", "")),
        str(row.get("postalcode", ""))
    ),
    axis=1
)

# Generate USPS-compatible work address
df["usps_waddress"] = df.apply(
    lambda row: generate_usps_address(
        str(row.get("waddress1", "")),
        str(row.get("waddress2", "")),
        str(row.get("wcity", "")),
        str(row.get("wstate", "")),
        str(row.get("wpostalcode", ""))
    ),
    axis=1
)

# Keep only relevant columns for output
df_output = df[["id", "usps_address", "usps_waddress"]]

# Save to new CSV
df_output.to_csv(output_file, index=False)

print(f"USPS-compatible addresses saved to {output_file}")

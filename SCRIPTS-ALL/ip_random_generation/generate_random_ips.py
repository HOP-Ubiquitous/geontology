import random
import pandas as pd
import valid_countries


def remove_duplicates(ips):
    return list(dict.fromkeys(ips))


def ip_next(ip):

    if ip[3] != "255":
        ip[3] = str(int(ip[3]) + 1)
    elif ip[2] != "255":
        ip[3] = '1'
        ip[2] = str(int(ip[2]) + 1)
    elif ip[1] != "255":
        ip[3] = '1'
        ip[2] = '0'
        ip[1] = str(int(ip[1]) + 1)
    else:
        ip[3] = '1'
        ip[2] = '0'
        ip[1] = '0'
        ip[0] = str(int(ip[0]) + 1)

    return ip


def generate_ips_series(ip_min, ip_max, times):
    ip_min_split = ip_min.split(".")
    ip_max_split = ip_max.split(".")

    ips = []

    i = 0

    current_ip = ip_min_split

    while i < times and current_ip != ip_max_split:
        current_ip = ip_next(current_ip)
        if current_ip[3] != "0" and current_ip[3] != "255":
            i += 1
            ips.append('.'.join(current_ip))

    return remove_duplicates(ips)


def save_ips_to_file(ips):
    fp = open(r'generated_ips.txt', 'a')
    fp.write("\n".join(ips) + str("\n"))


def convert_to_ip_address(ip_number):
    w = int(ip_number / 16777216) % 256
    x = int(ip_number / 65536) % 256
    y = int(ip_number / 256) % 256
    z = int(ip_number) % 256

    ip_address = str(w) + "." + str(x) + "." + str(y) + "." + str(z)
    return ip_address


def import_ip_locations(path):
    df = pd.read_csv(path, header=None)
    df.columns = ['ip_beginning', 'ip_end', 'country_code', 'country']
    df = df[df['country'].isin(valid_countries.countries)]
    df['ip_beginning'] = df['ip_beginning'].apply(convert_to_ip_address)
    df['ip_end'] = df['ip_end'].apply(convert_to_ip_address)

    return df


def generate_and_save_ips(ip_min, ip_max, times):
    ip_adds = generate_ips_series(ip_min, ip_max, times)
    save_ips_to_file(ip_adds)


def remove_blocks_overload(df, base_value):

    df2 = df
    df2['count'] = df.groupby('country')['country'].transform('count')
    df2 = df2[['country', 'count']].drop_duplicates()
    df2['overload'] = (df2['count'] - base_value).clip(0, None)
    df2 = df2.drop(df2[df2['overload'] == 0].index)
    df2['frac'] = df2['overload'] / df2['count']

    for country, to_remove in zip(df2['country'], df2['frac']):
        df = df.drop(df[df['country'] == country].sample(frac=to_remove).index)

    return df


if __name__ == "__main__":
    ip_ranges = import_ip_locations(r'ip_ranges.csv')
    # print(ip_ranges)
    ip_ranges = remove_blocks_overload(ip_ranges, 800)

    [generate_and_save_ips(row[0], row[1], 3) for row in zip(ip_ranges['ip_beginning'], ip_ranges['ip_end'])]
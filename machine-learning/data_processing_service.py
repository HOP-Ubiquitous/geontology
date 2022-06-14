from sklearn.preprocessing import LabelEncoder, OneHotEncoder


def encode_categorical(Y):
    labelencoder_y = LabelEncoder()
    return labelencoder_y.fit_transform(Y)

def standarize_variables(X):
    # Z-Score using pandas
    for column in X:
        X[column] = (X[column] - X[column].mean()) / X[column].std()

    return X

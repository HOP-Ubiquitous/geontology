import pandas as pd
from sklearn.model_selection import train_test_split

import random_forest_service

import data_processing_service

if __name__ == "__main__":

    df = pd.DataFrame({'Master_to_Client': [10, 39, 29, 56, 11, 58],
                       'Master_to_Bots': [20, 38, 25, 60, 14, 55],
                       'Client_to_Bots': [23, 33, 29, 75, 18, 59],
                       'Label': ["real", "real", "real", "vpn", "real", "vpn"]})

    # Seleccionar datos y labels
    X = df.loc[:, ["Master_to_Client", "Master_to_Bots", "Client_to_Bots"]]
    Y = df.loc[:, 'Label']

    # Codificar el dataframe
    Y = data_processing_service.encode_categorical(Y)
    X = data_processing_service.standarize_variables(X)

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=0)

    mse, r2, feature_importances = random_forest_service.random_forest(X, X_train, X_test, Y_train, Y_test, 20)

    Y_pred = random_forest_service.random_forest_predecir(X_train, Y_train, X_test)

    print(Y_pred)


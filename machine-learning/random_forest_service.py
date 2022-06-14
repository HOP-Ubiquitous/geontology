import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score


def random_forest(X, X_train, X_test, Y_train, Y_test, n_rep):
    mse = []
    r2 = []
    importances = []

    for i in range(0, n_rep):

        regr = RandomForestRegressor(n_estimators=1000)
        regr.fit(X_train, Y_train)
        y_pred = regr.predict(X_test)

        mse.append(mean_squared_error(Y_test, y_pred))
        r2.append(r2_score(Y_test, y_pred))

        importances = list(regr.feature_importances_)

    feature_importances = [(feature, round(importance, 2)) for feature, importance in zip(X, importances)]
    feature_importances = sorted(feature_importances, key=lambda x: x[1], reverse=True)

    return np.mean(mse), np.mean(r2), feature_importances


# Predice mediante un random forest
# Recibe el dataframe que se usará para entrenamiento, el que se quiere predecir,
# las variables que se usarán en el modelo y la variable objetivo
# Devuelve la lista de predicciones
def random_forest_predecir(X_train, Y_train, X_test):
    regr = RandomForestRegressor(n_estimators=1000)
    regr.fit(X_train, Y_train)
    y_pred = regr.predict(X_test)

    return y_pred


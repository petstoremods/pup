modes = []

def pup_mode(callback):
    modes.append(callback)

def normalize_value(feature, mode_config, value):
    if 'max' not in feature_config:
        return value

    max_value = mode_config['max']
    min_value = 0
    if 'min' in feature_config:
        min_value = mode_config['min']

    feature_min = feature.get_min()
    feature_max = feature.get_max()
    feature_diff = feature_max - feature_min

    value_diff = max_value - min_value

    # need to scale the feature with the game values
    # Example: if the device only goes (0-20), and you tie it to hp (0-100), then every 5 hp is one tick of the device feature
    tick_diff = value_diff / feature_diff
    value = value - min_value # in case it doesn't start at 0
    return round(value / tick_diff)
    
def normalize(feature, mode_config, value):
    normalized = normalize_value(feature, mode_config, value)
    return feature.get_execute_string(normaized)

@pup_mode
def vibrate_on_change(feature, mode_config):
    def generated(new_value):
        arg = mode_config['args'][0]
        feature.run(feature.get_execute_string(arg))

    return generated

@pup_mode
def vibrate_normalized(feature, mode_config):
    def generated(new_value):
        feature.run(normalize(feature, mode_config, new_value))

    return generated

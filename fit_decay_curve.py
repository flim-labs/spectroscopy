import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

def fit_decay_curve(x_values, y_values, plot_title="Decay Curve Fitting", num_components=3, B_component=False):
    def decay_model_1_with_B(t, A1, tau1, B):
        return A1 * np.exp(-t / tau1) + B

    def decay_model_2_with_B(t, A1, tau1, A2, tau2, B):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + B

    def decay_model_3_with_B(t, A1, tau1, A2, tau2, A3, tau3, B):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + A3 * np.exp(-t / tau3) + B

    def decay_model_4_with_B(t, A1, tau1, A2, tau2, A3, tau3, A4, tau4, B):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + A3 * np.exp(-t / tau3) + A4 * np.exp(-t / tau4) + B

    def decay_model_1(t, A1, tau1):
        return A1 * np.exp(-t / tau1)

    def decay_model_2(t, A1, tau1, A2, tau2):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2)

    def decay_model_3(t, A1, tau1, A2, tau2, A3, tau3):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + A3 * np.exp(-t / tau3)

    def decay_model_4(t, A1, tau1, A2, tau2, A3, tau3, A4, tau4):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + A3 * np.exp(-t / tau3) + A4 * np.exp(-t / tau4)

    decay_models = [decay_model_1, decay_model_2, decay_model_3, decay_model_4]
    decay_models_with_B = [decay_model_1_with_B, decay_model_2_with_B, decay_model_3_with_B, decay_model_4_with_B]

    decay_start = np.argmax(y_values)

    t_data = x_values[decay_start:]
    y_data = y_values[decay_start:]

    # Choose the model and initial guess based on the number of components
    if num_components < 1 or num_components > 4:
        return {"error": "Number of components must be between 1 and 4."}
    decay_model = decay_models[num_components - 1] if not B_component else decay_models_with_B[num_components - 1]
    initial_guess = [1] * (num_components * 2) if not B_component else [1] * (num_components * 2 + 1)

    if num_components == 1 and B_component == False:
        initial_guess[0] = max(y_data) / 2

    try:
        maxfev = 1000000000
        popt, pcov = curve_fit(decay_model, t_data, y_data, p0=initial_guess, maxfev=maxfev)
    except RuntimeError:
        return {"error": "Optimal parameters not found: Number of calls to function has reached maxfev."}

    fitted_params_text = 'Fitted parameters:\n'
    output_data = {}
    for i in range(num_components):
        y = i * 2
        SUM = sum(popt[even_index] for even_index in range(0, len(popt), 2))
        percentage_tau = popt[y] / (SUM + popt[-1]) if B_component else popt[y] / SUM
        fitted_params_text += f'τ{i + 1} = {popt[y + 1]:.4f} ns, {percentage_tau:.2%} of total\n'
        output_data[f'component_A{i + 1}'] = {'tau_ns': popt[y + 1], 'percentage': percentage_tau}
    if B_component:
        SUM = sum(popt[even_index] for even_index in range(0, len(popt), 2))
        percentage_tau = popt[-1] / (SUM + popt[-1])
        fitted_params_text += f'B = {percentage_tau:.2%} of total\n'
        output_data['component_B'] = popt[-1]

    fitted_values = decay_model(t_data, *popt)
    residuals = y_data - fitted_values

    # Plot the overall results and residuals
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Main plot
    ax1.scatter(x_values, y_values, label='Counts', color='lime', s=1)
    ax1.plot(t_data, decay_model(t_data, *popt), label='Fitted curve', color='red')
    ax1.set_xlabel('Time', color='white')
    ax1.set_ylabel('Counts', color='white')
    ax1.set_title(plot_title, color='white')
    ax1.legend(facecolor='grey', edgecolor='white')
    ax1.set_facecolor('black')
    fig.patch.set_facecolor('black')
    ax1.grid(color='white', linestyle='--', linewidth=0.5)
    ax1.tick_params(colors='white')
    fig.text(0.02, 0.02, fitted_params_text, fontsize=10, va='bottom', ha='left', color='white',
             bbox=dict(facecolor='black', alpha=0.8))

    # add initial missing x values to residuals to match the length of x_values
    residuals = np.concatenate((np.full(decay_start, 0), residuals))
    ax2.plot(x_values, residuals, color='cyan', linewidth=1)
    ax2.axhline(0, color='white', linestyle='--', linewidth=0.5)
    ax2.set_xlabel('Time', color='white')
    ax2.set_ylabel('Residuals', color='white')
    ax2.set_facecolor('black')
    ax2.grid(color='white', linestyle='--', linewidth=0.5)
    ax2.tick_params(colors='white')

    # Adjust layout to add an empty margin at the bottom
    plt.subplots_adjust(bottom=0.15)

    plt.tight_layout(rect=[0, 0.05, 1, 1])

    return {'plt': plt, 'output_data': output_data}
import numpy as np
from scipy.optimize import curve_fit
from scipy.special import wofz
import struct
import matplotlib.pyplot as plt

file_path = "<FILE-PATH>"
with open(file_path, "rb") as f:
    # first 4 bytes must be SP01
    # 'SP01' is an identifier for spectroscopy bin files
    if f.read(4) != b"SP01":
        print("Invalid data file")
        exit(0)

    # read metadata from file
    (json_length,) = struct.unpack("I", f.read(4))
    null = None
    metadata = eval(f.read(json_length).decode("utf-8"))

    # ENABLED CHANNELS
    if "channels" in metadata and metadata["channels"] is not None:
        print(
            "Enabled channels: "
            + (", ".join(["Channel " + str(ch + 1) for ch in metadata["channels"]]))
        )
    # BIN WIDTH (us)
    if "bin_width_micros" in metadata and metadata["bin_width_micros"] is not None:
        print("Bin width: " + str(metadata["bin_width_micros"]) + "us")
    # ACQUISITION TIME (duration of the acquisition)
    if (
        "acquisition_time_millis" in metadata
        and metadata["acquisition_time_millis"] is not None
    ):
        print(
            "Acquisition time: " + str(metadata["acquisition_time_millis"] / 1000) + "s"
        )
    # LASER PERIOD (ns)
    if "laser_period_ns" in metadata and metadata["laser_period_ns"] is not None:
        laser_period_ns = metadata["laser_period_ns"]
        print("Laser period: " + str(laser_period_ns) + "ns")
    else:
        print("Laser period not found in metadata.")
        exit(0)
    # TAU (ns)
    if "tau_ns" in metadata and metadata["tau_ns"] is not None:
        print("Tau: " + str(metadata["tau_ns"]) + "ns")

    channel_curves = [[] for _ in range(len(metadata["channels"]))]
    times = []
    number_of_channels = len(metadata["channels"])
    channel_values_unpack_string = "I" * 256

    # Read Spectroscopy data
    while True:
        data = f.read(8)
        if not data:
            break
        (time,) = struct.unpack("d", data)
        for i in range(number_of_channels):
            data = f.read(4 * 256)
            if len(data) < 4 * 256:
                break
            curve = struct.unpack(channel_values_unpack_string, data)
            channel_curves[i].append(np.array(curve))
        times.append(time / 1_000_000_000)

    num_bins = 256
    x_values = np.linspace(0, laser_period_ns, num_bins)

    ######### FITTING #############

    def decay_model_1_with_B(t, A1, tau1, B):
        return A1 * np.exp(-t / tau1) + B

    def decay_model_2_with_B(t, A1, tau1, A2, tau2, B):
        return A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + B

    def decay_model_3_with_B(t, A1, tau1, A2, tau2, A3, tau3, B):
        return (
            A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2) + A3 * np.exp(-t / tau3) + B
        )

    def decay_model_4_with_B(t, A1, tau1, A2, tau2, A3, tau3, A4, tau4, B):
        return (
            A1 * np.exp(-t / tau1)
            + A2 * np.exp(-t / tau2)
            + A3 * np.exp(-t / tau3)
            + A4 * np.exp(-t / tau4)
            + B
        )

    def decay_model_gaussian(t, A, mu, sigma):
        return A * np.exp(-((t - mu) ** 2) / (2 * sigma**2))

    def decay_model_exp_gaussian(t, A, tau, mu, sigma):
        return A * np.exp(-t / tau) * np.exp(-((t - mu) ** 2) / (2 * sigma**2))

    def decay_model_lorentzian(t, A, mu, gamma):
        return A * gamma**2 / ((t - mu) ** 2 + gamma**2)

    def decay_model_lorentzian_gaussian(t, A, mu, gamma, sigma):
        return (
            A
            * (gamma**2 / ((t - mu) ** 2 + gamma**2))
            * np.exp(-((t - mu) ** 2) / (2 * sigma**2))
        )

    def decay_model_voigt_profile(t, A, mu, sigma, gamma):
        z = ((t - mu) + 1j * gamma) / (sigma * np.sqrt(2))
        return A * np.real(wofz(z))

    def decay_model_power_law(t, A, alpha):
        return A * t ** (-alpha)

    model_formulas = {
        decay_model_1_with_B: "A1 * exp(-t / tau1) + B",
        decay_model_2_with_B: "A1 * exp(-t / tau1) + A2 * exp(-t / tau2) + B",
        decay_model_3_with_B: "A1 * exp(-t / tau1) + A2 * exp(-t / tau2) + A3 * exp(-t / tau3) + B",
        decay_model_4_with_B: "A1 * exp(-t / tau1) + A2 * exp(-t / tau2) + A3 * exp(-t / tau3) + A4 * exp(-t / tau4) + B",
        decay_model_gaussian: "A * exp(-(t - mu)**2 / (2 * sigma**2))",
        decay_model_exp_gaussian: "A * exp(-t / tau) * exp(-(t - mu)**2 / (2 * sigma**2))",
        decay_model_lorentzian: "A * gamma**2 / ((t - mu)**2 + gamma**2)",
        decay_model_lorentzian_gaussian: "A * (gamma**2 / ((t - mu)**2 + gamma**2)) * exp(-(t - mu)**2 / (2 * sigma**2))",
        decay_model_voigt_profile: "A * real(wofz(((t - mu) + 1j * gamma) / (sigma * sqrt(2))))",
        decay_model_power_law: "A * t**(-alpha)",
    }

    def fit_decay_curve(x_values, y_values, channel):
        decay_models = [
            (decay_model_1_with_B, [1, 1, 1]),
            (decay_model_2_with_B, [1, 1, 1, 1, 1]),
            (decay_model_3_with_B, [1, 1, 1, 1, 1, 1, 1]),
            (decay_model_4_with_B, [1, 1, 1, 1, 1, 1, 1, 1, 1]),
            (decay_model_gaussian, [1, 0, 1]),
            (decay_model_exp_gaussian, [1, 1, 0, 1]),
            (decay_model_lorentzian, [1, 0, 1]),
            (decay_model_lorentzian_gaussian, [1, 0, 1, 1]),
            (decay_model_voigt_profile, [1, 0, 1, 1]),
            (decay_model_power_law, [1, 1]),
        ]
        decay_start = np.argmax(y_values)

        if sum(y_values) == 0:
            return {"error": "All counts are zero.", "channel": channel}

        scale_factor = np.float64(1)
        if max(y_values) > 1000:
            scale_factor = np.float64(max(y_values) / 1000)
            y_values = [np.float64(y / scale_factor) for y in y_values]

        t_data = x_values[decay_start:]
        y_data = y_values[decay_start:]
        best_r2 = -np.inf
        best_fit = None
        best_model = None
        best_popt = None

        for model, initial_guess in decay_models:
            try:
                popt, pcov = curve_fit(
                    model, t_data, y_data, p0=initial_guess, maxfev=50000
                )
                fitted_values = model(t_data, *popt)
                residuals = np.array(y_data) - fitted_values
                SStot = np.sum((y_data - np.mean(y_data)) ** 2)
                SSres = np.sum(residuals**2)
                r2 = 1 - SSres / SStot
                if r2 > best_r2:
                    best_r2 = r2
                    best_fit = fitted_values
                    best_model = model
                    best_popt = popt
            except RuntimeError as e:
                continue

        if best_fit is None:
            return {"error": "Optimal parameters not found for any model."}

        output_data = {}
        num_components = (len(best_popt) - 1) // 2
        fitted_params_text = "Fitted parameters:\n"
        for i in range(num_components):
            y = i * 2
            SUM = sum(
                best_popt[even_index] for even_index in range(0, len(best_popt) - 1, 2)
            )
            percentage_tau = best_popt[y] / (SUM + best_popt[-1])
            fitted_params_text += (
                f"τ{i + 1} = {best_popt[y + 1]:.4f} ns, {percentage_tau:.2%} of total\n"
            )
            output_data[f"component_A{i + 1}"] = {
                "tau_ns": best_popt[y + 1],
                "percentage": percentage_tau,
            }

        SUM = sum(
            best_popt[even_index] for even_index in range(0, len(best_popt) - 1, 2)
        )
        percentage_tau = best_popt[-1] / (SUM + best_popt[-1])
        fitted_params_text += f"B = {percentage_tau:.2%} of total\n"
        output_data["component_B"] = best_popt[-1]
        fitted_params_text += f"R² = {best_r2:.4f}\n"

        residuals = np.concatenate((np.full(decay_start, 0), residuals))

        return {
            "x_values": x_values,
            "y_data": y_data,
            "t_data": t_data,
            "fitted_values": best_fit,
            "residuals": residuals,
            "fitted_params_text": fitted_params_text,
            "output_data": output_data,
            "scale_factor": scale_factor,
            "decay_start": decay_start,
            "channel": channel,
        }

    valid_results = []

    for i in range(len(channel_curves)):
        channel = metadata["channels"][i]
        y = np.sum(channel_curves[i], axis=0)
        if y.ndim == 0:
            y = np.array([y])
        x = x_values
        result = fit_decay_curve(x, y, channel)
        if "error" in result:
            print(f"Skipping channel {channel + 1}: {result['error']}")
            continue
        valid_results.append(result)

    num_plots = len(valid_results)
    plots_per_row = 4
    num_rows = int(np.ceil(num_plots / plots_per_row))

    fig = plt.figure(figsize=(5 * plots_per_row, 5 * num_rows + 2))
    gs = fig.add_gridspec(
        num_rows * 2, plots_per_row, height_ratios=[3] * num_rows + [1] * num_rows
    )

    axes = np.array(
        [
            [fig.add_subplot(gs[2 * row, col]) for col in range(plots_per_row)]
            for row in range(num_rows)
        ]
    )
    residual_axes = np.array(
        [
            [fig.add_subplot(gs[2 * row + 1, col]) for col in range(plots_per_row)]
            for row in range(num_rows)
        ]
    )

    for i, result in enumerate(valid_results):
        row = i // plots_per_row
        col = i % plots_per_row

        truncated_x_values = result["x_values"][result["decay_start"] :]
        counts_y_data = np.array(result["y_data"]) * result["scale_factor"]
        fitted_y_data = np.array(result["fitted_values"]) * result["scale_factor"]

        axes[row, col].scatter(
            truncated_x_values, counts_y_data, label="Counts", color="lime", s=1
        )
        axes[row, col].plot(
            result["t_data"], fitted_y_data, label="Fitted curve", color="red"
        )
        axes[row, col].set_xlabel("Time", color="white")
        axes[row, col].set_ylabel("Counts", color="white")
        axes[row, col].set_title(f"Channel {result['channel'] + 1}", color="white")
        axes[row, col].legend(facecolor="grey", edgecolor="white")
        axes[row, col].set_facecolor("black")
        axes[row, col].grid(color="white", linestyle="--", linewidth=0.5)
        axes[row, col].tick_params(colors="white")

        residual_axes[row, col].plot(
            result["x_values"], result["residuals"], color="cyan", linewidth=1
        )
        residual_axes[row, col].axhline(0, color="white", linestyle="--", linewidth=0.5)
        residual_axes[row, col].set_xlabel("Time", color="white")
        residual_axes[row, col].set_ylabel("Residuals", color="white")
        residual_axes[row, col].set_facecolor("black")
        residual_axes[row, col].grid(color="white", linestyle="--", linewidth=0.5)
        residual_axes[row, col].tick_params(colors="white")

        text_box_props = dict(boxstyle="round", facecolor="black", alpha=0.8)
        residual_axes[row, col].text(
            0.02,
            -0.6,
            result["fitted_params_text"],
            transform=residual_axes[row, col].transAxes,
            fontsize=10,
            va="top",
            ha="left",
            color="white",
            bbox=text_box_props,
        )

    for i in range(num_plots, num_rows * plots_per_row):
        row = i // plots_per_row
        col = i % plots_per_row
        axes[row, col].axis("off")
        residual_axes[row, col].axis("off")

    fig.patch.set_facecolor("black")

    plt.tight_layout(rect=[0, 0.1, 1, 1])
    plt.show()

const API_KEY = "API_KEY_HERE";
document.addEventListener("DOMContentLoaded", function () {
  const symbol = document.getElementById("symbol").textContent;
  async function getData() {
    const url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${symbol}&apikey=${API_KEY}`;
    const response = await fetch(url);
    const data = await response.json();
    return data;
  }
  getData().then((data) => {
    console.log(data);
    const timeSeries = data["Time Series (Daily)"];
    console.log(timeSeries);
    const dates = Object.keys(timeSeries).reverse();
    const price = dates.map((date) => ({
      x: new Date(date), // Convert date string to Date object
      y: parseFloat(timeSeries[date]["4. close"]),
    }));
    renderChart(dates,price);
  });

  function renderChart(dates, price) {
    const ctx = document.getElementById("chart").getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: dates,
        datasets: [
          {
            label: `${symbol} Closing Prices`,
            data: price,
            borderColor: "rgba(75, 192, 192, 1)",
            backgroundColor: "rgba(75, 192, 192, 0.2)",
            fill: false,
          },
        ],
      },
      options: {
        scales: {
          x: {
            type: "time",
            time: {
              unit: "day",
              tooltipFormat: 'll',
            },
            title: {
              display: true,
              text: 'Date',
            },
          },
          y: {
            title: {
              display: true,
              text: 'Closing Price',
            },
          },
        },
      },
    });
  }
});

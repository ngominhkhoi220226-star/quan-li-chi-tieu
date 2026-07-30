#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

using namespace std;

int main() {
    ifstream file("data.csv");
    string line;
    long long total = 0;

    if (file.is_open()) {
        // Đọc từng dòng trong file CSV
        while (getline(file, line)) {
            if (line.empty()) continue;
            
            stringstream ss(line);
            string date, category, content, amount_str;
            
            // Cấu trúc mới: Ngày,Danh mục,Nội dung,Số tiền
            getline(ss, date, ',');
            getline(ss, category, ',');
            getline(ss, content, ',');
            getline(ss, amount_str, ',');

            if (!amount_str.empty()) {
                total += stoll(amount_str); // Cộng dồn số tiền
            }
        }
        file.close();
    }

    // Ghi tổng tiền ra file text để Python đọc lại
    ofstream outfile("total.txt");
    outfile << total;
    outfile.close();

    return 0;
}
